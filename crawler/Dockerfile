# Build context: repository root
#   docker build -f crawler/Dockerfile -t wikipulse/crawler .
FROM golang:1.23 AS build

WORKDIR /src
COPY crawler/go.mod crawler/go.sum ./
RUN go mod download
COPY crawler/ ./
RUN CGO_ENABLED=0 go build -trimpath -o /out/crawler .

FROM gcr.io/distroless/static-debian12:nonroot

COPY --from=build /out/crawler /crawler

ENTRYPOINT ["/crawler"]
