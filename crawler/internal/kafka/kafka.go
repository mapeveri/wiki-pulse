// Package kafka publishes crawler events to Redpanda / Kafka.
package kafka

import (
	"bytes"
	"context"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/linkedin/goavro/v2"
	"github.com/segmentio/kafka-go"
)

// Producer publishes Avro events to a single topic, keyed by article so all
// events for the same article land on the same partition.
type Producer struct {
	writer   *kafka.Writer
	codec    *goavro.Codec
	schemaID uint32
}

// NewProducer returns a producer writing to the given topic.
func NewProducer(brokers []string, topic string) (*Producer, error) {
	schemaName := "articles"
	if strings.HasPrefix(topic, "pageviews") {
		schemaName = "pageviews"
	}
	schemaDir := os.Getenv("WIKIPULSE_SCHEMA_DIR")
	if schemaDir == "" {
		schemaDir = "schemas"
		if _, err := os.Stat(filepath.Join(schemaDir, schemaName+".avsc")); err != nil {
			schemaDir = "../schemas"
		}
	}
	schemaBytes, err := os.ReadFile(filepath.Join(schemaDir, schemaName+".avsc"))
	if err != nil {
		return nil, fmt.Errorf("read Avro schema %s: %w", schemaName, err)
	}
	codec, err := goavro.NewCodec(string(schemaBytes))
	if err != nil {
		return nil, fmt.Errorf("parse Avro schema %s: %w", schemaName, err)
	}
	registryURL := os.Getenv("SCHEMA_REGISTRY_URL")
	if registryURL == "" {
		registryURL = "http://localhost:8081"
	}
	schemaID, err := registerSchema(registryURL, topic+"-value", string(schemaBytes))
	if err != nil {
		return nil, fmt.Errorf("register Avro schema for %s: %w", topic, err)
	}
	return &Producer{
		codec: codec, schemaID: schemaID,
		writer: &kafka.Writer{
			Addr:         kafka.TCP(brokers...),
			Topic:        topic,
			Balancer:     &kafka.Hash{},
			RequiredAcks: kafka.RequireAll,
			Compression:  kafka.Snappy,
			BatchTimeout: 50 * time.Millisecond,
		},
	}, nil
}

// Publish sends a single event, serialized as an Avro binary datum.
func (p *Producer) Publish(ctx context.Context, key string, event any) error {
	value, err := p.codec.BinaryFromNative(nil, avroNative(event))
	if err != nil {
		return err
	}
	var header [5]byte
	header[0] = 0
	binary.BigEndian.PutUint32(header[1:], p.schemaID)
	wireValue := append(header[:], value...)
	return p.writer.WriteMessages(ctx, kafka.Message{
		Key:   []byte(key),
		Value: wireValue,
	})
}

func registerSchema(registryURL, subject, schema string) (uint32, error) {
	client := &http.Client{Timeout: 10 * time.Second}
	base := strings.TrimRight(registryURL, "/")
	configBody, _ := json.Marshal(map[string]string{"compatibility": "BACKWARD"})
	configReq, err := http.NewRequest(http.MethodPut, base+"/config", bytes.NewReader(configBody))
	if err != nil {
		return 0, err
	}
	configReq.Header.Set("Content-Type", "application/vnd.schemaregistry.v1+json")
	configResp, err := client.Do(configReq)
	if err != nil {
		return 0, err
	}
	io.Copy(io.Discard, configResp.Body)
	configResp.Body.Close()
	if configResp.StatusCode < 200 || configResp.StatusCode >= 300 {
		return 0, fmt.Errorf("set compatibility returned %s", configResp.Status)
	}

	body, err := json.Marshal(map[string]string{"schema": schema, "schemaType": "AVRO"})
	if err != nil {
		return 0, err
	}
	req, err := http.NewRequest(http.MethodPost, base+"/subjects/"+url.PathEscape(subject)+"/versions", bytes.NewReader(body))
	if err != nil {
		return 0, err
	}
	req.Header.Set("Content-Type", "application/vnd.schemaregistry.v1+json")
	resp, err := client.Do(req)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		responseBody, _ := io.ReadAll(resp.Body)
		return 0, fmt.Errorf("register schema returned %s: %s", resp.Status, responseBody)
	}
	var result struct {
		ID uint32 `json:"id"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return 0, err
	}
	return result.ID, nil
}

func avroNative(event any) map[string]interface{} {
	// The crawler's wire record is an Avro map with signed long values.
	values := map[string]interface{}{}
	if encoded, ok := event.(interface{ AvroRecord() map[string]interface{} }); ok {
		return encoded.AvroRecord()
	}
	return values
}

// Close flushes pending messages and closes the writer.
func (p *Producer) Close() error {
	return p.writer.Close()
}
