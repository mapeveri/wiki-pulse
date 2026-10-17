// Package wikipedia fetches a Wikipedia article and extracts simple content
// structure metrics (word count, sections, links) from its HTML.
package wikipedia

import (
	"context"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
)

// Article mirrors a row of the raw.articles table.
type Article struct {
	Project       string `json:"project"`
	Article       string `json:"article"`
	URL           string `json:"url"`
	Title         string `json:"title"`
	WordCount     uint32 `json:"word_count"`
	SectionCount  uint32 `json:"section_count"`
	InternalLinks uint32 `json:"internal_links"`
	ExternalLinks uint32 `json:"external_links"`
	CrawledAt     string `json:"crawled_at"`
}

// Client crawls Wikipedia articles.
type Client struct {
	http      *http.Client
	userAgent string
}

// NewClient returns a crawler client with a descriptive User-Agent.
func NewClient(userAgent string) *Client {
	return &Client{
		http:      &http.Client{Timeout: 30 * time.Second},
		userAgent: userAgent,
	}
}

// Crawl fetches a single article and returns its content metrics.
// The project is a Wikimedia project prefix such as "en.wikipedia".
func (c *Client) Crawl(ctx context.Context, project, title string) (*Article, error) {
	domain := project + ".org"
	pageURL := fmt.Sprintf("https://%s/wiki/%s", domain, url.PathEscape(title))
	apiURL := fmt.Sprintf("https://%s/api/rest_v1/page/html/%s", domain, url.PathEscape(title))

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, apiURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", c.userAgent)
	req.Header.Set("Accept", "text/html; charset=utf-8")

	resp, err := c.http.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status %d for %q", resp.StatusCode, apiURL)
	}

	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return nil, err
	}

	content := doc.Find(".mw-parser-output").First()
	if content.Length() == 0 {
		content = doc.Find("body").First()
	}
	if content.Length() == 0 {
		return nil, fmt.Errorf("no content found for %q", title)
	}

	displayTitle := strings.TrimSpace(doc.Find("title").First().Text())
	if displayTitle == "" {
		displayTitle = strings.ReplaceAll(title, "_", " ")
	}

	internalLinks := content.Find(`a[href^="./"], a[href^="/wiki/"]`).Length()
	externalLinks := content.Find(`a[href^="http"]`).FilterFunction(
		func(_ int, s *goquery.Selection) bool {
			href, _ := s.Attr("href")
			return !strings.Contains(href, "wikipedia.org")
		},
	).Length()

	return &Article{
		Project:       project,
		Article:       title,
		URL:           pageURL,
		Title:         displayTitle,
		WordCount:     uint32(len(strings.Fields(content.Text()))),
		SectionCount:  uint32(content.Find("h2, h3").Length()),
		InternalLinks: uint32(internalLinks),
		ExternalLinks: uint32(externalLinks),
		CrawledAt:     time.Now().UTC().Format("2006-01-02 15:04:05"),
	}, nil
}
