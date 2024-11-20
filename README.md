[![CI](https://github.com/OneOffTech/parxy/actions/workflows/ci.yml/badge.svg)](https://github.com/OneOffTech/parxy/actions/workflows/ci.yml) [![Build Docker Image](https://github.com/OneOffTech/parxy/actions/workflows/docker.yml/badge.svg)](https://github.com/OneOffTech/parxy/actions/workflows/docker.yml)

# Parxy

Parxy is a gateway service that provides a unified approach to accessing PDF parsing services and libraries. It is available as a library and as an http-based application.

> [!NOTE]  
> Parxy is under active development.

## Getting started

The easiest way to get started with Parxy is to use the Docker image provided.

```bash
docker pull ghcr.io/OneOffTech/parxy:main
```

A sample [`docker-compose.yaml` file](./docker-compose.yaml) is available within the repository.


> Please refer to [Releases](https://github.com/OneOffTech/parxy/releases) and [Packages](https://github.com/OneOffTech/parxy/pkgs/container/parxy) for the available tags.


## Usage

Parxy expose a web-based application programming interface (API). The available API receive a PDF file via a URL and return the extracted text as a JSON response.

The exposed service is unauthenticated therefore consider exposing it only within a trusted network. If you plan to make it available publicly consider adding a reverse proxy with authentication in front.

### Text extraction endpoint

The service expose only one endpoint `/extract-text` that accepts a `POST` request
with the following input as a `json` body:

- `url`: the URL of the PDF file to process.
- `mime_type`: the mime type of the file (it is expected to be `application/pdf`).
- `driver`: two drivers are currently implemented `pymupdf` and `pdfact`. It defines the extraction backend to use.

> [!WARNING]
> The processing is performed synchronously

The response is a JSON structure following the [Parse Document Model](https://github.com/OneOffTech/parse-document-model-python).

In particular, the structure is as follows:
- `category`: A string specifying the node category, which is `doc`
- `content`: A list of `page` nodes representing the pages within the document.

Each page node contains the following information:
- `category`: A string specifying the node category, which is `page`.
- `attributes`: A list containing attributes of the page. Currently, it includes only `page`, the number of the node page.
- `content`: A list of chunk each representing a segment of text extracted from the page.

In particular, each `content` contains the following information:
  - `role`: The role of the chunk in the document (e.g., _heading_, _body_, etc.)
  - `text`: The text extracted from the chunk.
  - `marks`: A list of marks that characterize the text extracted from the chunk.
  - `attributes`: A list containing attributes of the chunk, currently including:
    - A list of `bounding_box` attributes that contain the text. Each bounding box is identified by 4 coordinated: 
    `min_x`,`min_y`, `max_x`, `max_y` and `page`, which is the page number where the bounding box is located.

The `marks` of the chunks contains:
- `category`: the type of the mark, which can be: `bold`, `italic`, `textStyle`, `link`

If the mark type is `textStyle`, it includes additional attributes:
- `font`: An object representing the font of the text chunk. 
Each font is represented by `name`, `id`, and `size`. Available only using `pdfact` driver.
- `color`: Which is the color of the text chunk. 
Each color is represented by `r`, `g`, `b` and `id`. Available only using `pdfact` driver.

if the mark category is `link`, it provides the `url` of the link.

### Error handling

The service can return the following errors

| code  | message                       | description                                                             |
|-------|-------------------------------|-------------------------------------------------------------------------|
| `422` | No url found in request       | In case the `url` field in the request is missing                       |
| `422` | No mime_type found in request | In case the `mime_type` field in the request is missing                 |
| `422` | Unsupported file type         | In case the file is not a PDF                                           |
| `500` | Error while saving file       | In case it was not possible to download the file from the specified URL |
| `500` | Error while parsing file      | In case it was not possible to open the file after download             |


The body of the response can contain a JSON with the following fields:

- `code` the error code
- `message` the error description
- `type` the type of the error

```json
{
  "code": 500,
  "message": "Error while parsing file",
  "type": "Internal Server Error",
}
```

## Development

Parxy is built using [FastAPI](https://fastapi.tiangolo.com/) and Python 3.9.

Given the selected stack the development requires:

- [Python 3.9](https://www.python.org/) with PIP
- [Docker](https://www.docker.com/) (optional) to test the build


Install all the required dependencies:

```bash
pip install -r requirements.txt
```

Run the local development application using:

```bash
fastapi dev text_extractor_api/main.py
```


### Testing

_to be documented_


## Contributing

Thank you for considering contributing to Parxy! The contribution guide can be found in the [CONTRIBUTING.md](./.github/CONTRIBUTING.md) file.


## Supporters

The project is provided and supported by [OneOff-Tech (UG)](https://oneofftech.de).

<p align="left"><a href="https://oneofftech.de" target="_blank"><img src="https://raw.githubusercontent.com/OneOffTech/.github/main/art/oneofftech-logo.svg" width="200"></a></p>


## Security Vulnerabilities

If you discover a security vulnerability within PDF Text Extract, please send an e-mail to OneOff-Tech team via [security@oneofftech.xyz](mailto:security@oneofftech.xyz). All security vulnerabilities will be promptly addressed.
