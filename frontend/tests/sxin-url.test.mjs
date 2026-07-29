import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const appSource = await readFile(new URL('../src/App.tsx', import.meta.url), 'utf8');

test('SXin assistant iframe uses the port 81 SXin mock-login URL', () => {
  assert.match(
    appSource,
    /src="http:\/\/10\.10\.3\.100:81\/iot-os\/sxin\/#\/mockLogin"/,
  );
  assert.doesNotMatch(appSource, /10\.10\.3\.100:2026/);
  assert.doesNotMatch(appSource, /192\.168\.11\.194:10997/);
});
