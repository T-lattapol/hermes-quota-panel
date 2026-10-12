import test from 'node:test';
import assert from 'node:assert/strict';
import {isQuotaIndicatorId} from '../gnome-extension/click-routing.js';

test('direct click is restricted to the two quota indicators', () => {
  assert.equal(isQuotaIndicatorId('codex-quota'), true);
  assert.equal(isQuotaIndicatorId('claude-quota'), true);
  assert.equal(isQuotaIndicatorId('software-update'), false);
  assert.equal(isQuotaIndicatorId(null), false);
});
