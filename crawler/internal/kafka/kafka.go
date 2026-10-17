// Package kafka publishes crawler events to Redpanda / Kafka.
package kafka

import (
	"context"
	"encoding/json"
	"time"

	"github.com/segmentio/kafka-go"
)

// Producer publishes JSON events to a single topic, keyed by article so all
// events for the same article land on the same partition.
type Producer struct {
	writer *kafka.Writer
}

// NewProducer returns a producer writing to the given topic.
func NewProducer(brokers []string, topic string) *Producer {
	return &Producer{
		writer: &kafka.Writer{
			Addr:         kafka.TCP(brokers...),
			Topic:        topic,
			Balancer:     &kafka.Hash{},
			RequiredAcks: kafka.RequireAll,
			BatchTimeout: 50 * time.Millisecond,
		},
	}
}

// Publish sends a single event, serialized as JSON.
func (p *Producer) Publish(ctx context.Context, key string, event any) error {
	value, err := json.Marshal(event)
	if err != nil {
		return err
	}
	return p.writer.WriteMessages(ctx, kafka.Message{
		Key:   []byte(key),
		Value: value,
	})
}

// Close flushes pending messages and closes the writer.
func (p *Producer) Close() error {
	return p.writer.Close()
}
