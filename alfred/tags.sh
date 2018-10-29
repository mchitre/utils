#!/bin/bash

echo '{"items":['
find /Users/mandar/Dropbox/apps/Quiver.qvlibrary -name meta.json -exec grep '^    "' {} \; | sed 's/^    "//' | sed 's/".*$//' | sort | uniq | perl -pe 'chop; $_="{ \"arg\": \"$_\", \"title\": \"$_\" },";'
echo ']}'

