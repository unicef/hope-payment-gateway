AZURE_BLOB = "https://*.blob.core.windows.net"

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "style-src": [
            "'self'",
            "'unsafe-inline'",
            AZURE_BLOB,
        ],
        "script-src": [
            "'self'",
            "'unsafe-inline'",
            "'unsafe-eval'",
            AZURE_BLOB,
        ],
        "img-src": [
            "'self'",
            "data:",
            AZURE_BLOB,
        ],
        "font-src": [
            "'self'",
            "data:",
            AZURE_BLOB,
        ],
        "connect-src": [
            "'self'",
            AZURE_BLOB,
        ],
        "frame-src": ["'self'"],
        "object-src": ["'none'"],
        "base-uri": ["'self'"],
        "frame-ancestors": ["'self'"],
    }
}
