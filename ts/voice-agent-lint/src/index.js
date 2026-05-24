// voice-agent-lint — Node reference (zero-dep).
// Same RTL-001..017 rules as the Python helper; suitable for Express /
// Fastify CI gates that don't want to shell out to Python.

'use strict';

const ALLOWED_PARAM_TYPES = new Set(['string', 'number', 'integer', 'boolean', 'array', 'object']);
const ALLOWED_ANALYSIS_TYPES = new Set(['string', 'number', 'boolean', 'enum']);
const BCP47_RE = /^[a-z]{2,3}(-[A-Z]{2}|-[0-9]{3})?$/;
const NGROK_LOCAL_RE = /(ngrok\.(io|app)|\blocalhost\b|\b127\.0\.0\.1\b|\.local(?::|\/|$))/i;
const PLACEHOLDER_RE = /<<[A-Z0-9_]+>>/;


function lint(agent) {
  const findings = [];
  const F = (rule, severity, message, path) => findings.push({ rule, severity, message, path });

  const cf = agent.conversationFlow || {};
  const tools = Array.isArray(agent.tools) ? agent.tools : [];
  const toolsByName = new Map();
  for (const t of tools) if (t && t.name) toolsByName.set(t.name, t);
  const toolsById = new Set(tools.filter(t => t && t.id).map(t => t.id));

  // RTL-001
  if (!('is_transfer_cf' in cf)) F('RTL-001', 'ERROR',
    'conversationFlow.is_transfer_cf is missing',
    'conversationFlow.is_transfer_cf');

  // RTL-006
  if (!cf.start_node_id) F('RTL-006', 'ERROR',
    'conversationFlow.start_node_id is missing',
    'conversationFlow.start_node_id');

  const nodes = Array.isArray(cf.nodes) ? cf.nodes : [];
  const nodeIds = nodes.map(n => n && n.id);
  const nodeIdSet = new Set(nodeIds);
  if (cf.start_node_id && !nodeIdSet.has(cf.start_node_id)) {
    F('RTL-006', 'ERROR',
      `start_node_id '${cf.start_node_id}' does not match any node`,
      'conversationFlow.start_node_id');
  }

  // RTL-005
  const seen = new Set();
  for (let i = 0; i < nodeIds.length; i++) {
    if (seen.has(nodeIds[i])) {
      F('RTL-005', 'ERROR', `duplicate node id '${nodeIds[i]}'`, `conversationFlow.nodes[${i}].id`);
    }
    seen.add(nodeIds[i]);
  }

  // RTL-003, RTL-014
  nodes.forEach((n, i) => {
    if (!n || n.type !== 'function') return;
    if (!n.tool_id) {
      F('RTL-014', 'ERROR', 'function node has empty tool_id', `conversationFlow.nodes[${i}].tool_id`);
    } else if (!toolsByName.has(n.tool_id) && !toolsById.has(n.tool_id)) {
      F('RTL-003', 'ERROR',
        `function node references unknown tool '${n.tool_id}'`,
        `conversationFlow.nodes[${i}].tool_id`);
    }
  });

  // RTL-004, RTL-013
  const edges = Array.isArray(cf.edges) ? cf.edges : [];
  const edgeIds = new Set();
  edges.forEach((e, i) => {
    if (!e) return;
    if (e.id && edgeIds.has(e.id)) {
      F('RTL-013', 'ERROR', `duplicate edge id '${e.id}'`, `conversationFlow.edges[${i}].id`);
    }
    if (e.id) edgeIds.add(e.id);
    if (e.destination_node_id && !nodeIdSet.has(e.destination_node_id)) {
      F('RTL-004', 'ERROR',
        `edge destination_node_id '${e.destination_node_id}' does not resolve`,
        `conversationFlow.edges[${i}].destination_node_id`);
    }
  });

  // Tools-related rules
  tools.forEach((t, i) => {
    if (!t || typeof t !== 'object') return;
    const url = t.url || '';
    if (url && !url.startsWith('https://') && !PLACEHOLDER_RE.test(url)) {
      F('RTL-009', 'ERROR', `tool url is not https: ${url}`, `tools[${i}].url`);
    }
    if (url && NGROK_LOCAL_RE.test(url) && !PLACEHOLDER_RE.test(url)) {
      F('RTL-016', 'ERROR',
        `tool url contains ngrok / localhost / .local: ${url}`,
        `tools[${i}].url`);
    }
    if ('webhook_secret' in t && typeof t.webhook_secret === 'string' && !PLACEHOLDER_RE.test(t.webhook_secret)) {
      F('RTL-017', 'WARN', 'webhook_secret appears to be plaintext', `tools[${i}].webhook_secret`);
    }
    const params = t.parameters || {};
    const required = params.required;
    if ('parameters' in t && (required == null || (Array.isArray(required) && required.length === 0))) {
      F('RTL-002', 'ERROR',
        `tools[${i}] '${t.name}' has empty parameters.required`,
        `tools[${i}].parameters.required`);
    }
    const props = params.properties || {};
    for (const [pname, pdef] of Object.entries(props)) {
      if (!pdef || typeof pdef !== 'object') continue;
      if (!pdef.description) {
        F('RTL-011', 'ERROR',
          `parameter '${pname}' is missing description`,
          `tools[${i}].parameters.properties.${pname}.description`);
      }
      if (pdef.type && !ALLOWED_PARAM_TYPES.has(pdef.type)) {
        F('RTL-012', 'ERROR',
          `parameter '${pname}' has invalid type '${pdef.type}'`,
          `tools[${i}].parameters.properties.${pname}.type`);
      }
    }
  });

  // RTL-007
  (agent.post_call_analysis_data || []).forEach((p, i) => {
    if (p && !ALLOWED_ANALYSIS_TYPES.has(p.type)) {
      F('RTL-007', 'ERROR',
        `post_call_analysis_data[${i}].type='${p.type}' not in allowed set`,
        `post_call_analysis_data[${i}].type`);
    }
  });

  // RTL-008
  if (agent.language && !BCP47_RE.test(String(agent.language))) {
    F('RTL-008', 'ERROR',
      `language '${agent.language}' is not BCP-47 (try 'en-US', 'es-MX')`,
      'language');
  }

  return findings;
}


function summarize(findings) {
  const errors = findings.filter(f => f.severity === 'ERROR').length;
  const warns  = findings.filter(f => f.severity === 'WARN').length;
  return {
    total: findings.length,
    errors,
    warns,
    verdict: errors ? 'BLOCK DEPLOY' : warns ? 'OK (with warnings)' : 'OK',
  };
}


module.exports = { lint, summarize };
