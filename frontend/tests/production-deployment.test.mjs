import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

function readConfig(path) {
  try {
    return readFileSync(new URL(path, import.meta.url), 'utf8');
  } catch (error) {
    if (error?.code === 'ENOENT') {
      return '';
    }
    throw error;
  }
}

const dockerfile = readConfig('../Dockerfile');
const nginx = readConfig('../nginx.conf');

test('frontend uses a production Nginx image', () => {
  assert.match(dockerfile, /FROM node:22 AS build/);
  assert.match(dockerfile, /RUN npm run build/);
  assert.match(dockerfile, /FROM nginx:1\.27-alpine/);
  assert.match(dockerfile, /COPY --from=build \/app\/dist \/usr\/share\/nginx\/html/);
  assert.doesNotMatch(dockerfile, /npm.*run.*dev/);
});

test('Nginx preserves port, SPA routes, and streaming API semantics', () => {
  assert.match(nginx, /listen 5173;/);
  assert.match(nginx, /try_files \$uri \$uri\/ \/index\.html;/);
  assert.match(nginx, /location \/api\//);
  assert.match(nginx, /proxy_pass http:\/\/backend:8081;/);
  assert.match(nginx, /proxy_buffering off;/);
  assert.match(nginx, /proxy_request_buffering off;/);
  assert.match(nginx, /proxy_read_timeout 3600s;/);
});

test('Nginx compresses production text assets without buffering streams', () => {
  assert.match(nginx, /gzip on;/);
  assert.match(nginx, /gzip_types text\/css application\/javascript application\/json image\/svg\+xml;/);
  assert.doesNotMatch(nginx, /gzip_types[^;]*video\/x-flv/);
});
