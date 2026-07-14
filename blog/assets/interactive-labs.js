(function () {
  function number(value, fallback) {
    var parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function setText(root, selector, value) {
    var node = root.querySelector(selector);
    if (node) node.textContent = value;
  }

  function setupFdc(root) {
    var threshold = root.querySelector('[data-fdc-threshold]');
    var chart = root.querySelector('[data-fdc-chart]');
    if (!threshold || !chart) return;

    var normal = [0.3, -0.8, 1.1, -0.4, 0.7, 1.6, -1.3, 0.2, 2.1, -0.6, 0.9, -1.8, 0.5, 1.3, -0.9, 0.1, 2.3, -1.1, 0.6, -0.2];
    var faults = [3.4, 2.8, 2.6, 4.1];

    function render() {
      var limit = number(threshold.value, 2.5);
      var falseAlarms = normal.filter(function (z) { return Math.abs(z) >= limit; }).length;
      var detected = faults.filter(function (z) { return Math.abs(z) >= limit; }).length;
      var samples = normal.map(function (z) { return { z: z, fault: false }; })
        .concat(faults.map(function (z) { return { z: z, fault: true }; }));

      chart.replaceChildren();
      samples.forEach(function (sample, index) {
        var bar = document.createElement('span');
        var flagged = Math.abs(sample.z) >= limit;
        bar.className = 'sim-run' + (sample.fault ? ' is-fault' : '') + (flagged ? ' is-flagged' : '');
        bar.style.setProperty('--run-height', Math.max(12, Math.min(100, Math.abs(sample.z) / 4.2 * 100)) + '%');
        bar.title = (root.dataset.runText || 'Run') + ' ' + (index + 1) + ': z=' + sample.z.toFixed(1)
          + (sample.fault ? ', ' + (root.dataset.faultText || 'known fault') : ', ' + (root.dataset.normalText || 'normal'));
        chart.appendChild(bar);
      });

      setText(root, '[data-fdc-value]', limit.toFixed(1) + ' sigma');
      setText(root, '[data-fdc-false]', String(falseAlarms));
      setText(root, '[data-fdc-detected]', detected + ' / ' + faults.length);
      setText(root, '[data-fdc-result]', falseAlarms === 0 && detected === faults.length
        ? root.dataset.passText
        : root.dataset.reviewText);
      root.dataset.state = falseAlarms === 0 && detected === faults.length ? 'pass' : 'review';
    }

    threshold.addEventListener('input', render);
    render();
  }

  function setupRag(root) {
    var inputs = Array.from(root.querySelectorAll('[data-rag-metric]'));
    if (!inputs.length) return;
    var gates = { retrieval: 85, grounded: 90, permission: 100, freshness: 95, refusal: 95 };

    function render() {
      var failures = [];
      inputs.forEach(function (input) {
        var key = input.dataset.ragMetric;
        var value = number(input.value, 0);
        setText(root, '[data-rag-value="' + key + '"]', value + '%');
        if (value < gates[key]) failures.push(input.dataset.label + ' ' + value + '% < ' + gates[key] + '%');
      });
      var passed = failures.length === 0;
      setText(root, '[data-rag-result]', passed ? root.dataset.passText : root.dataset.failText);
      setText(root, '[data-rag-reasons]', passed ? root.dataset.passReason : failures.join(' | '));
      root.dataset.state = passed ? 'pass' : 'review';
    }

    inputs.forEach(function (input) { input.addEventListener('input', render); });
    render();
  }

  function setupTakt(root) {
    var inputs = Array.from(root.querySelectorAll('[data-takt-input]'));
    if (!inputs.length) return;

    function render() {
      var values = {};
      inputs.forEach(function (input) {
        values[input.dataset.taktInput] = number(input.value, 0);
        setText(root, '[data-takt-value="' + input.dataset.taktInput + '"]', input.value + (input.dataset.unit || ''));
      });
      var shiftSeconds = values.shift * 3600;
      var attribution = number(values.attribution, 0);
      var downtime = values.response * values.events * attribution / 100;
      var planned = Math.floor(shiftSeconds / values.takt);
      var effectiveCycle = Math.max(values.takt, values.cycle);
      var cycleActual = Math.floor(shiftSeconds / effectiveCycle);
      var actual = Math.max(0, Math.floor((shiftSeconds - downtime) / effectiveCycle));
      var cycleLost = Math.max(0, planned - cycleActual);
      var agentLost = Math.max(0, cycleActual - actual);
      var lost = cycleLost + agentLost;
      setText(root, '[data-takt-planned]', planned.toLocaleString());
      setText(root, '[data-takt-actual]', actual.toLocaleString());
      setText(root, '[data-takt-cycle-lost]', cycleLost.toLocaleString());
      setText(root, '[data-takt-agent-lost]', agentLost.toLocaleString());
      setText(root, '[data-takt-lost]', lost.toLocaleString());
      setText(root, '[data-takt-downtime]', Math.round(downtime / 60).toLocaleString() + ' ' + (root.dataset.minuteText || 'min'));
      root.dataset.state = lost === 0 ? 'pass' : 'review';
    }

    inputs.forEach(function (input) { input.addEventListener('input', render); });
    render();
  }

  function init() {
    document.querySelectorAll('[data-fdc-sim]').forEach(setupFdc);
    document.querySelectorAll('[data-rag-eval-sim]').forEach(setupRag);
    document.querySelectorAll('[data-takt-sim]').forEach(setupTakt);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
