// Package clickhouse writes crawler output into the ClickHouse raw layer
// through the HTTP interface using the JSONEachRow format.
package clickhouse

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/wikipulse/crawler/internal/wikipedia"
)

// Config holds the ClickHouse connection settings.
type Config struct {
	URL      string
	Database string
	User     string
	Password string
}

var httpClient = &http.Client{Timeout: 30 * time.Second}

// InsertArticles loads the given articles into "<database>.articles".
func InsertArticles(ctx context.Context, cfg Config, articles []wikipedia.Article) error {
	var body bytes.Buffer
	encoder := json.NewEncoder(&body)
	for _, article := range articles {
		if err := encoder.Encode(article); err != nil {
			return err
		}
	}

	query := fmt.Sprintf("INSERT INTO %s.articles FORMAT JSONEachRow", cfg.Database)
	endpoint := fmt.Sprintf("%s/?query=%s", strings.TrimRight(cfg.URL, "/"), url.QueryEscape(query))

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, &body)
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	if cfg.User != "" {
		req.Header.Set("X-ClickHouse-User", cfg.User)
	}
	if cfg.Password != "" {
		req.Header.Set("X-ClickHouse-Key", cfg.Password)
	}

	resp, err := httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		message, _ := io.ReadAll(io.LimitReader(resp.Body, 4096))
		return fmt.Errorf("clickhouse insert failed (%d): %s", resp.StatusCode, strings.TrimSpace(string(message)))
	}
	return nil
}
