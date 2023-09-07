#!/bin/bash

set -eou pipefail

case "$1" in
    dev)
        echo TODO
    ;;
    *)
        exec "$@"
    ;;
esac
