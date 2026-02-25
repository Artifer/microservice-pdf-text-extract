# PDF Text Extractor Microservice

Microservice for extracting text from PDF files. Used by Power Automate flows in a Copilot Studio tenderbot.

## Security

The service uses API key authentication. Set the `API_KEY` environment variable.

- If `API_KEY` is not set: all requests are allowed (for local testing)
- If `API_KEY` is set: requests must include header `x-api-key: <your-key>`

## Endpoints

### POST /extract

Extract text from a single PDF file.

**Parameters (form-data):**

- `file`: PDF file (max 50MB)

**Returns:** JSON

```json
{
  "filename": "leidraad.pdf",
  "pages": 42,
  "total_characters": 85230,
  "text": "volledige tekst van alle pagina's...",
  "pages_text": [
    { "page": 1, "text": "tekst van pagina 1..." },
    { "page": 2, "text": "tekst van pagina 2..." }
  ]
}
```

### POST /extract-multiple

Extract text from multiple PDF files.

**Parameters (form-data):**

- `files`: multiple PDF files (max 50MB each)

**Returns:** JSON

```json
{
  "documents": [
    {
      "filename": "leidraad.pdf",
      "pages": 42,
      "total_characters": 85230,
      "text": "volledige tekst..."
    },
    {
      "filename": "bijlage_a.pdf",
      "pages": 8,
      "total_characters": 12450,
      "text": "volledige tekst..."
    }
  ]
}
```

### GET /health

Health check endpoint.

## Local testing

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

### Test single file extraction

```bash
curl -X POST http://localhost:8000/extract \
  -F "file=@test.pdf" \
  -H "x-api-key: test123"
```

### Test multiple file extraction

```bash
curl -X POST http://localhost:8000/extract-multiple \
  -F "files=@document1.pdf" \
  -F "files=@document2.pdf" \
  -H "x-api-key: test123"
```

## Power Automate Integration

### Single extraction (HTTP action):

- Method: POST
- URI: `https://your-service/extract`
- Headers:
  - `x-api-key`: your API key
- Body: Form-data with `file` parameter containing the PDF
