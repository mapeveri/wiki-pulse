// Command crawler fetches content structure metrics for the tracked articles
// and loads them into the ClickHouse raw layer.
//
// Usage:
//
//	crawler --topics-file ingestion/topics.txt
//	crawler --topics-file ingestion/topics.txt --concurrency 8
package main

import (
	"bufio"
	"context"
	"flag"
	"fmt"
	"os"
	"strings"
	"sync"

	"github.com/wikipulse/crawler/internal/clickhouse"
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
	chURL := flag.String("clickhouse-url", "http://localhost:8123", "ClickHouse HTTP endpoint")
	chDB := flag.String("clickhouse-db", "raw", "ClickHouse database")
	chUser := flag.String("clickhouse-user", "default", "ClickHouse user")
	chPass := flag.String("clickhouse-password", "", "ClickHouse password")
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

	articles := make([]wikipedia.Article, 0, len(topics))
	var (
		mu       sync.Mutex
		wg       sync.WaitGroup
		failures int
		sem      = make(chan struct{}, *concurrency)
	)

	for _, topic := range topics {
		wg.Add(1)
		sem <- struct{}{}
		go func(topic string) {
			defer wg.Done()
			defer func() { <-sem }()

			article, err := client.Crawl(ctx, *project, topic)
			if err != nil {
				mu.Lock()
				failures++
				mu.Unlock()
				fmt.Fprintf(os.Stderr, "  %s: %v\n", topic, err)
				return
			}
			mu.Lock()
			articles = append(articles, *article)
			mu.Unlock()
			fmt.Printf("  %s: %d words, %d sections, %d internal links\n",
				article.Title, article.WordCount, article.SectionCount, article.InternalLinks)
		}(topic)
	}
	wg.Wait()

	if len(articles) == 0 {
		return fmt.Errorf("all %d topics failed to crawl", len(topics))
	}
	if failures > 0 {
		fmt.Fprintf(os.Stderr, "%d of %d topics failed (continuing)\n", failures, len(topics))
	}

	cfg := clickhouse.Config{
		URL:      *chURL,
		Database: *chDB,
		User:     *chUser,
		Password: *chPass,
	}
	if err := clickhouse.InsertArticles(ctx, cfg, articles); err != nil {
		return err
	}

	fmt.Printf("Loaded %d articles into %s.articles\n", len(articles), *chDB)
	return nil
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
