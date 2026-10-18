// Command crawler fetches content structure metrics for the tracked articles
// and publishes one event per article to Redpanda.
//
// The sink (ingestion.sink) is the component that writes these events into the
// ClickHouse raw layer.
//
// Usage:
//
//	crawler --topics-file ingestion/topics.txt
//	crawler --topics-file ingestion/topics.txt --kafka-brokers localhost:9092
package main

import (
	"bufio"
	"context"
	"flag"
	"fmt"
	"os"
	"strings"
	"sync"

	"github.com/wikipulse/crawler/internal/kafka"
	"github.com/wikipulse/crawler/internal/wikipedia"
)

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
}

func run() error {
	topicsFile := flag.String("topics-file", "ingestion/topics.txt", "file with one article title per line")
	project := flag.String("project", "en.wikipedia", "Wikimedia project prefix")
	concurrency := flag.Int("concurrency", 4, "number of concurrent crawlers")
	userAgent := flag.String(
		"user-agent",
		"seo-marketing-analytics-platform/0.1 (https://github.com/your-user/seo-marketing-analytics-platform)",
		"User-Agent header sent to Wikipedia",
	)
	brokers := flag.String("kafka-brokers", defaultBrokers(), "comma-separated Kafka/Redpanda brokers")
	topic := flag.String("topic", "articles.raw", "target topic")
	flag.Parse()

	topics, err := readTopics(*topicsFile)
	if err != nil {
		return err
	}
	if len(topics) == 0 {
		return fmt.Errorf("no topics found in %s", *topicsFile)
	}

	ctx := context.Background()
	client := wikipedia.NewClient(*userAgent)
	producer := kafka.NewProducer(splitBrokers(*brokers), *topic)
	defer producer.Close()

	var (
		mu       sync.Mutex
		wg       sync.WaitGroup
		failures int
		sem      = make(chan struct{}, *concurrency)
	)

	for _, topic := range topics {
		wg.Add(1)
		sem <- struct{}{}
		go func(article string) {
			defer wg.Done()
			defer func() { <-sem }()

			parsed, err := client.Crawl(ctx, *project, article)
			if err != nil {
				mu.Lock()
				failures++
				mu.Unlock()
				fmt.Fprintf(os.Stderr, "  %s: %v\n", article, err)
				return
			}
			if err := producer.Publish(ctx, parsed.Article, parsed); err != nil {
				mu.Lock()
				failures++
				mu.Unlock()
				fmt.Fprintf(os.Stderr, "  %s: publish failed: %v\n", article, err)
				return
			}
			fmt.Printf("  %s: %d words, %d sections, %d internal links\n",
				parsed.Title, parsed.WordCount, parsed.SectionCount, parsed.InternalLinks)
		}(topic)
	}
	wg.Wait()

	if failures > 0 {
		fmt.Fprintf(os.Stderr, "%d of %d topics failed\n", failures, len(topics))
	}
	fmt.Printf("Published %d events to %s\n", len(topics)-failures, *topic)
	if failures > 0 {
		// Exit non-zero so the CronJob retries; re-publishing is safe because
		// the raw layer is idempotent.
		return fmt.Errorf("%d of %d topics failed", failures, len(topics))
	}
	return nil
}

// defaultBrokers reads the shared KAFKA_BOOTSTRAP_SERVERS variable so the
// crawler and the Python services resolve brokers from the same configuration.
func defaultBrokers() string {
	if brokers := os.Getenv("KAFKA_BOOTSTRAP_SERVERS"); brokers != "" {
		return brokers
	}
	return "localhost:9092"
}

func splitBrokers(brokers string) []string {
	parts := strings.Split(brokers, ",")
	for i := range parts {
		parts[i] = strings.TrimSpace(parts[i])
	}
	return parts
}

func readTopics(path string) ([]string, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var topics []string
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		topics = append(topics, line)
	}
	return topics, scanner.Err()
}
