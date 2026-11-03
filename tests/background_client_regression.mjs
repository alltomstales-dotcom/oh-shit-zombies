import assert from 'node:assert/strict';import fs from 'node:fs';
const {normalizeBackground}=await import('data:text/javascript;base64,'+Buffer.from(fs.readFileSync('app/static/js/backgrounds.js','utf8')).toString('base64'));
const data={occupations:[{id:'generalist'},{id:'medic'}],traits:[{id:'balanced'},{id:'nimble'}]};
assert.deepEqual(normalizeBackground({occupation:'medic',trait:'nimble'},data),{occupation:'medic',trait:'nimble'});
assert.deepEqual(normalizeBackground({occupation:'removed',trait:'removed'},data),{occupation:'generalist',trait:'balanced'});
assert.deepEqual(normalizeBackground(null,data),{occupation:'generalist',trait:'balanced'});
assert.deepEqual(normalizeBackground(null,null),{occupation:'generalist',trait:'balanced'});
console.log('New-life background preferences validate against the server catalog.');
