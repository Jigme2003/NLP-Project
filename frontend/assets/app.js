const $ = (id) => document.getElementById(id);
let activeReport = null;

function setStatus(text, healthy = true) {
  $('serviceStatus').textContent = text;
  $('serviceStatus').style.color = healthy ? '#2f7658' : '#d86c4c';
}

function buildTailoredRecommendations(metrics) {
  const {
    fileName = 'local-demo-video.mp4',
    speaker = 'Speaker',
    transcript = '',
    wordCount = 0,
    wpm = 0,
    fillerCount = 0,
    pauseSeconds = 0,
    contentScore = 0,
    deliveryScore = 0,
    confidenceScore = 0,
    visualScore = 0,
    learnedScore = 0,
    scriptProvided = false,
    scriptAlignment = 0,
    messageClarity = 0,
    evidenceScore = 0,
    audienceEngagement = 0,
    speechPresence = 0
  } = metrics || {};

  const recs = [];
  if (fillerCount > 6) recs.push(`Trim filler words: this presentation is carrying about ${fillerCount} hesitations, so removing them will make the delivery sound more deliberate.`);
  if (pauseSeconds > 12) recs.push(`Shorten the pauses between key points; the current pacing includes about ${pauseSeconds.toFixed(1)}s of dead air, which weakens momentum.`);
  if (wpm < 110 || wpm > 165) recs.push(`Adjust the pacing toward a stronger speaking rhythm; the current rate is ${Number(wpm).toFixed(0)} wpm and would benefit from a steadier cadence.`);
  if (contentScore < 72) recs.push(`Strengthen the opening and structure so the core point lands sooner; the current message structure is ${Number(contentScore).toFixed(0)}/100.`);
  if (messageClarity < 72) recs.push(`Simplify the wording and keep each point to one clear message; clarity is currently ${Number(messageClarity).toFixed(0)}/100.`);
  if (visualScore < 72) recs.push(`Improve lighting and framing: the visual signal is only ${Number(visualScore).toFixed(0)}/100, which lowers the presentation’s polish.`);
  if (confidenceScore < 72) recs.push(`Project more assurance in the first 20 seconds; confidence is currently ${Number(confidenceScore).toFixed(0)}/100.`);
  if (evidenceScore < 72) recs.push('Support the main claim with a concrete example, result, or proof point so the argument feels more convincing and credible.');
  if (audienceEngagement < 72) recs.push('Add a sharper audience hook and a stronger closing call to action to make the presentation more compelling.');
  if (scriptProvided && scriptAlignment < 72) recs.push(`Align the spoken message more closely with the prepared script; script alignment is ${Number(scriptAlignment).toFixed(0)}/100, so tighten the phrasing and emphasis.`);
  if (learnedScore !== undefined && learnedScore < 60) recs.push(`The learned quality signal is weaker than expected at ${Number(learnedScore).toFixed(0)}/100, so focus on cleaner pacing and more confident delivery.`);
  if (speechPresence < 63) recs.push('Check microphone placement and room noise so the voice stays consistent and clean throughout the presentation.');
  if (!recs.length) recs.push(`Strong presentation profile for ${speaker}. Keep this pacing and structure consistent and protect the delivery rhythm in the next take.`);
  return recs.slice(0, 5);
}

function buildDemoReport(file, speaker, script) {
  const fileName = file?.name || 'local-demo-video.mp4';
  const transcript = (script || '').trim() || `This presentation focuses on the core message and audience value in ${fileName}.`;
  const wordCount = Math.max(80, transcript.split(/\s+/).length * 2);
  const wpm = 118 + (wordCount % 24);
  const fillerCount = Math.max(2, Math.round(wordCount / 70));
  const pauseSeconds = 2.3 + (wordCount % 9) * 0.55;
  const qualityBias = (speaker.length + fileName.length + transcript.length) % 14;
  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
  const contentScore = clamp(48 + (transcript.length % 18) - fillerCount * 2.5 - pauseSeconds * 2.4 + qualityBias * 0.6, 22, 82);
  const deliveryScore = clamp(46 + (wpm - 110) * 0.38 - fillerCount * 3.1 - pauseSeconds * 2.2 + (speaker.length % 9), 20, 84);
  const confidenceScore = clamp(52 - fillerCount * 2.4 + (speaker.length % 12) - pauseSeconds * 1.6, 20, 86);
  const visualScore = clamp(56 + (fileName.length % 12) - Math.max(0, 6 - (speaker.length % 7)) * 1.5, 18, 78);
  const learnedScore = clamp(52 + (transcript.length % 20) - fillerCount * 2.2 - pauseSeconds * 1.8, 18, 85);
  const overallScore = clamp(Math.round((contentScore * 0.38 + deliveryScore * 0.27 + visualScore * 0.18 + confidenceScore * 0.17) * 0.92), 18, 88);
  const scriptAlignment = script && script.trim() ? Math.min(95, Math.max(40, contentScore + (speaker.length % 12))) : 0;
  const tailoredRecommendations = buildTailoredRecommendations({
    fileName,
    speaker,
    transcript,
    wordCount,
    wpm,
    fillerCount,
    pauseSeconds,
    contentScore,
    deliveryScore,
    confidenceScore,
    visualScore,
    learnedScore,
    scriptProvided: Boolean(script && script.trim()),
    scriptAlignment,
    messageClarity: Math.max(32, contentScore - 8),
    evidenceScore: Math.max(35, contentScore - 5),
    audienceEngagement: Math.max(30, contentScore - 7),
    speechPresence: Math.max(20, deliveryScore - 18)
  });
  const breakdown = {
    message_structure: contentScore,
    content_quality: contentScore,
    fluency: deliveryScore,
    confidence: confidenceScore,
    visual_quality: visualScore,
    gaze_quality: Math.min(92, 72 + (fileName.length % 12)),
    learned_score: learnedScore,
    recommendations: tailoredRecommendations
  };

  const contentAnalysis = {
    status: 'Local demo assessment',
    strengths: ['Clear central message', 'Strong audience focus', 'Good pacing rhythm'],
    improvements: ['Trim filler words', 'Tighten transition phrasing', 'Sharpen closing emphasis'],
    metrics: {
      word_count: wordCount,
      sentence_count: 5 + (wordCount % 4),
      lexical_diversity: 63 + (transcript.length % 20),
      speaking_rate: wpm
    }
  };

  const reading = {
    status: 'Local demo gaze review',
    likelihood: 62 + (fileName.length % 20),
    confidence: 72 + (speaker.length % 18),
    note: 'This is a browser-only demo estimate and not a real camera analysis.',
    reference_script_provided: Boolean(script && script.trim()),
    script_alignment: { status: script ? 'Good alignment' : 'No script supplied' }
  };

  return {
    filename: fileName,
    overall_score: overallScore,
    overview: {
      filename: fileName,
      overall_score: overallScore,
      grade: overallScore >= 85 ? 'A' : overallScore >= 75 ? 'B' : 'C',
      status: overallScore >= 80 ? 'Pass / Good' : 'Improve',
      grading_mode: 'Local browser-only demo assessment',
      module_selection: {
        modules: { visual: true, audio: true, content: true, gaze: true, learned: true },
        reasons: { visual: 'Local demo quality check', audio: 'Local demo delivery check', content: 'Local content review', gaze: 'Local gaze proxy', learned: 'Local demo learned signal enabled' },
        note: 'This demo mode is intentionally offline and does not call any API, but the learned metric remains visible.'
      },
      weights: {
        visual_quality: 0.05,
        fluency: 0.2,
        content_quality: 0.35,
        gaze_quality: 0.15,
        learned_score: 0.1,
        confidence: 0.15
      },
      rubric: {
        dimensions: [
          { title: 'Message Structure', score: contentScore, description: 'Opening, flow, and clarity' },
          { title: 'Delivery', score: deliveryScore, description: 'Rhythm and vocal control' },
          { title: 'Confidence', score: confidenceScore, description: 'Presence and assurance' },
          { title: 'Visual Quality', score: visualScore, description: 'Framing and camera readiness' }
        ]
      }
    },
    visual_quality: {
      metrics: { duration_sec: 120, resolution: '1920x1080', avg_sharpness: 72, avg_brightness: 64, avg_motion: 18 },
      classifications: { framing: 'Stable', brightness: 'Healthy', motion: 'Controlled' },
      feedback: 'Local demo mode keeps the UI working without backend processing.',
      score: visualScore
    },
    reading_assessment: reading,
    presentation: {
      metrics: {
        transcript: transcript,
        duration_sec: 120,
        word_count: wordCount,
        wpm: wpm,
        filler_count: fillerCount,
        pitch_variation: 32 + (wordCount % 18),
        pause_seconds: pauseSeconds,
        speech_ratio: 0.8 + (wordCount % 8) / 100,
        energy_variation: 40 + (wordCount % 24),
        avg_word_prob: 0.82 + (transcript.length % 12) / 100
      },
      score: deliveryScore,
      status: 'Local demo delivery review',
      feedback: 'The local demo model emphasizes pacing, articulation, and clear message cues.'
    },
    communication_assessment: {
      overall_score: overallScore,
      grade: overallScore >= 85 ? 'A' : overallScore >= 75 ? 'B' : 'C',
      overall_metrics: {
        scores: {
          visual_quality: visualScore,
          fluency: deliveryScore,
          content_quality: contentScore,
          gaze_quality: Math.min(92, 72 + (fileName.length % 12)),
          learned_score: learnedScore,
          confidence: confidenceScore
        },
        weights: {
          visual_quality: 0.05,
          fluency: 0.2,
          content_quality: 0.35,
          gaze_quality: 0.15,
          learned_score: 0.1,
          confidence: 0.15
        }
      },
      breakdown: breakdown,
      recommendations: breakdown.recommendations
    },
    content_analysis: contentAnalysis,
    ml_score: learnedScore,
    ml_rank_eligible: true
  };
}

function renderBatchResults(reports) {
  const rankedReports = [...reports].sort((left, right) => {
    const leftScore = left.error ? -1 : Number(left.overall_score ?? left.overview?.overall_score ?? 0);
    const rightScore = right.error ? -1 : Number(right.overall_score ?? right.overview?.overall_score ?? 0);
    return rightScore - leftScore;
  });
  renderComparisonTable(rankedReports);
  return rankedReports.find((report) => !report.error) || null;
}

function renderComparisonTable(reports) {
  const body = $('comparisonBody');
  const summary = $('comparisonSummary');
  if (!body || !summary) return;
  body.innerHTML = '';
  summary.textContent = `${reports.length} video${reports.length === 1 ? '' : 's'} ranked`;
  reports.forEach((report, index) => {
    const breakdown = report.communication_assessment?.breakdown || {};
    const row = document.createElement('tr');
    row.tabIndex = report.error ? -1 : 0;
    row.className = report.error ? 'comparison-error' : '';
    const values = [
      `#${index + 1}`,
      report.filename || 'Video',
      report.error ? 'Error' : `${Number(report.overall_score ?? report.overview?.overall_score ?? 0).toFixed(0)}/100`,
      report.error ? 'Unavailable' : (report.overview?.grade || 'Not rated'),
      report.error ? '—' : `${Number(breakdown.message_structure ?? breakdown.content_quality ?? 0).toFixed(0)}`,
      report.error ? '—' : `${Number(breakdown.fluency || 0).toFixed(0)}`,
      report.error ? '—' : `${Number(breakdown.confidence || 0).toFixed(0)}`,
      report.error ? '—' : `${Number(breakdown.visual_quality || 0).toFixed(0)}`
    ];
    values.forEach((value, valueIndex) => {
      const cell = document.createElement('td');
      cell.textContent = value;
      if (valueIndex === 2 && !report.error) cell.className = 'comparison-score';
      row.appendChild(cell);
    });
    if (!report.error) {
      row.addEventListener('click', () => renderReport(report, reports.length));
      row.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') renderReport(report, reports.length);
      });
    }
    body.appendChild(row);
  });
}

function renderRubric(report) {
  const dimensions = report.overview?.rubric?.dimensions || [];
  const selection = report.overview?.module_selection || {};
  const reasons = selection.reasons || {};
  const reasonByKey = {
    content_quality: reasons.content,
    technical: reasons.visual,
    delivery: reasons.audio,
    articulation: reasons.audio,
    confidence: reasons.audio,
    vocal_expression: reasons.audio,
    recognition_confidence: reasons.content,
    gaze_quality: reasons.gaze,
    facial_expressiveness: reasons.expression,
    script_adherence: report.script_adherence?.status || 'Add a reference script and ensure speech is transcribed to compare alignment.',
    learned_score: reasons.learned
  };
  const assessed = [];
  const notAssessed = [];
  dimensions.forEach((item) => {
    const hasScore = item.score !== null && Number.isFinite(Number(item.score));
    const card = document.createElement('article');
    card.className = 'rubric-card';
    const title = document.createElement('span');
    title.className = 'metric-caption';
    title.textContent = item.title;
    const score = document.createElement('strong');
    score.textContent = hasScore ? Number(item.score).toFixed(0) : 'Not assessed';
    const description = document.createElement('small');
    const weight = (Number(item.weight || 0) * 100).toFixed(1);
    description.textContent = `${item.description} · ${weight}% of score`;
    card.append(title, score, description);
    if (hasScore) {
      const bar = document.createElement('div');
      bar.className = 'rubric-bar';
      const fill = document.createElement('i');
      fill.style.width = `${Math.max(0, Math.min(100, Number(item.score)))}%`;
      bar.appendChild(fill);
      card.appendChild(bar);
      assessed.push(card);
    } else {
      const reason = document.createElement('small');
      reason.className = 'rubric-unassessed-reason';
      reason.textContent = reasonByKey[item.key] || 'This optional measure was not available for this recording.';
      card.appendChild(reason);
      notAssessed.push(card);
    }
  });

  const grid = $('rubricGrid');
  grid.replaceChildren(...assessed);
  if (notAssessed.length) {
    const details = document.createElement('details');
    details.className = 'rubric-unassessed';
    const summary = document.createElement('summary');
    summary.textContent = `${notAssessed.length} optional metric${notAssessed.length === 1 ? '' : 's'} not assessed`;
    details.append(summary, ...notAssessed);
    grid.appendChild(details);
  }
}

function renderRecommendations(items) {
  $('recommendationList').innerHTML = (items || []).map((item) => `<li>${item}</li>`).join('');
}

function renderSkillCoaching(report) {
  const list = $('recommendationList');
  const plan = report.communication_assessment?.skill_coaching || [];
  if (!plan.length) {
    renderRecommendations(report.communication_assessment?.breakdown?.recommendations || report.communication_assessment?.recommendations || []);
    return;
  }

  list.replaceChildren();
  plan.forEach((item) => {
    const card = document.createElement('li');
    card.className = 'skill-coaching-item';
    const title = document.createElement('strong');
    title.textContent = item.area;
    const evidence = document.createElement('span');
    evidence.textContent = item.observed;
    const action = document.createElement('p');
    action.textContent = item.action;
    const practice = document.createElement('small');
    practice.textContent = `Practice: ${item.practice} Goal: ${item.target}`;
    card.append(title, evidence, action, practice);
    list.appendChild(card);
  });
}

function renderAssessmentCoverage(report) {
  const selection = report.overview?.module_selection || {};
  const modules = selection.modules || {};
  const reasons = selection.reasons || {};
  const labels = { visual: 'Video quality', audio: 'Audio delivery', content: 'Message content', gaze: 'Eye-line signal', expression: 'Facial movement', learned: 'Learned model' };
  const aggregate = report.communication_assessment?.overall_metrics || {};
  const scores = aggregate.scores || {};
  const weights = aggregate.weights || {};
  const componentKeys = {
    visual: ['visual_quality'],
    audio: ['fluency', 'pronunciation', 'confidence', 'vocal_expression', 'recognition_confidence'],
    content: ['content_quality', 'script_adherence'],
    gaze: ['gaze_quality'],
    expression: ['facial_expressiveness'],
    learned: ['learned_score']
  };
  const rows = Object.entries(labels).map(([key, label]) => {
    const active = Boolean(modules[key]);
    const values = componentKeys[key].filter((name) => name in scores).map((name) => Number(scores[name]));
    const score = values.length ? (values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(0) : '—';
    return `<tr class="${active ? 'ledger-included' : 'ledger-skipped'}"><td>${label} summary</td><td><b>${active ? 'Included' : 'Not assessed'}</b></td><td>${active ? score : '—'}</td><td>—</td><td>${reasons[key] || 'No evidence available'}</td></tr>`;
  });
  Object.entries(scores).forEach(([key, score]) => {
    const label = key.replaceAll('_', ' ');
    rows.push(`<tr class="ledger-included"><td>${label}</td><td><b>Included</b></td><td>${Number(score).toFixed(0)}</td><td>${(Number(weights[key] || 0) * 100).toFixed(1)}%</td><td>Used in the weighted overall score</td></tr>`);
  });
  $('gradingLedgerBody').innerHTML = rows.join('');
  const coverage = Number(aggregate.coverage_percent || 0).toFixed(0);
  $('coverageNote').textContent = `Overall score = the weighted average of the included metric scores shown below. Evidence coverage: ${coverage}%. Missing signals are skipped, not treated as measured zeros. Facial movement and eye-line are visual proxies, not measures of motivation or intent.`;
}

function renderReport(report, count) {
  activeReport = report;
  const overview = report.overview || {};
  const breakdown = report.communication_assessment?.breakdown || {};
  const speech = report.presentation?.metrics || {};
  const content = report.content_analysis || {};
  const contentMetrics = content.metrics || {};
  const reading = report.reading_assessment || {};

  $('emptyState').classList.add('hidden');
  $('resultsPanel').classList.remove('hidden');
  $('reportTitle').textContent = report.filename || 'Presenter report';
  $('reportStatus').textContent = `${count} video${count === 1 ? '' : 's'} reviewed`;
  $('overallScore').textContent = overview.overall_score ?? 0;
  $('gradeBadge').textContent = overview.grade || 'Not rated';
  $('statusValue').textContent = overview.status || 'Reviewed';
  const aggregate = report.communication_assessment?.overall_metrics || {};
  const coverage = Number(aggregate.coverage_percent || 0);
  $('evidenceCoverage').textContent = `Evidence coverage: ${coverage.toFixed(0)}%`;
  $('wpmValue').textContent = Number(speech.wpm || 0).toFixed(0);
  $('fillerValue').textContent = Number(speech.filler_count || 0).toFixed(0);
  $('pauseValue').textContent = `${Number(speech.pause_seconds || 0).toFixed(1)}s`;
  $('pitchValue').textContent = Number(speech.pitch_variation || 0).toFixed(1);
  $('speechRatioValue').textContent = `${(Number(speech.speech_ratio || 0) * 100).toFixed(0)}%`;
  $('contentStatus').textContent = content.status || 'Transcript unavailable';
  $('contentWords').textContent = contentMetrics.word_count || 0;
  $('contentSentences').textContent = contentMetrics.sentence_count || 0;
  $('contentVocabulary').textContent = `${Number(contentMetrics.lexical_diversity || 0).toFixed(1)}%`;
  $('contentFeedback').textContent = [...(content.strengths || []), ...(content.improvements || [])].join(' ') || 'Content feedback will appear when a transcript is available.';
  $('readingStatus').textContent = reading.status || 'Insufficient camera evidence';
  $('readingLikelihood').textContent = `${Number(reading.likelihood || 0).toFixed(0)}%`;
  $('readingConfidence').textContent = `${Number(reading.confidence || 0).toFixed(0)}%`;
  $('readingFeedback').textContent = reading.reference_script_provided
    ? `${reading.note || ''} Reference script alignment: ${reading.script_alignment?.status || 'not available'}.`
    : (reading.note || 'Eye-line analysis is a proxy only; it cannot prove whether a presenter is reading.');
  const expression = report.reading_assessment || {};
  $('expressionStatus').textContent = expression.facial_expressiveness_available
    ? 'Visible movement samples available'
    : 'Not enough face samples';
  $('expressionScore').textContent = expression.facial_expressiveness_score == null
    ? '—'
    : `${Number(expression.facial_expressiveness_score).toFixed(0)}/100`;
  $('expressionSamples').textContent = Number(expression.facial_expression_samples || 0).toFixed(0);
  $('expressionNote').textContent = expression.note || 'Visible face movement is only a proxy. The system does not infer motivation or emotion.';
  renderAssessmentCoverage(report);
  renderRubric(report);
  renderTalkCoach(report.talk_coaching);
  renderSkillCoaching(report);
  $('downloadReportButton').disabled = false;
}

function renderTalkCoach(coaching) {
  const list = $('talkCoachList');
  list.replaceChildren();
  if (!coaching?.available) {
    $('talkCoachProgress').textContent = 'Transcript needed';
    $('talkCoachNote').textContent = coaching?.note || 'A transcript is needed for talk-structure suggestions.';
    return;
  }

  $('talkCoachProgress').textContent = `${coaching.signal_count} / ${coaching.total_signals} cues`;
  $('talkCoachNote').textContent = coaching.note;
  coaching.signals.forEach((signal) => {
    const item = document.createElement('li');
    item.className = `talk-coach-item ${signal.detected ? 'is-detected' : 'is-missing'}`;
    const title = document.createElement('strong');
    title.textContent = `${signal.detected ? 'Cue found' : 'Try adding'} · ${signal.title}`;
    const evidence = document.createElement('span');
    evidence.textContent = signal.detected ? signal.evidence : signal.suggestion;
    item.append(title, evidence);
    list.appendChild(item);
  });
}

function downloadReport(report) {
  const breakdown = report.communication_assessment?.breakdown || {};
  const coaching = report.talk_coaching || {};
  const recommendations = breakdown.recommendations || report.communication_assessment?.recommendations || [];
  const dimensions = report.overview?.rubric?.dimensions || [];
  const lines = [
    'PRESENTER PERFORMANCE REPORT',
    `Video: ${report.filename || 'Presentation'}`,
    `Overall score: ${report.overview?.overall_score ?? 'Not available'} / 100`,
    `Grade: ${report.overview?.grade || 'Not rated'}`,
    `Evidence coverage: ${Number(report.communication_assessment?.overall_metrics?.coverage_percent || 0).toFixed(0)}%`,
    '',
    'RUBRIC',
    ...dimensions.map((item) => `${item.title}: ${item.score == null ? 'Not assessed' : `${Number(item.score).toFixed(0)}/100`} (${(Number(item.weight || 0) * 100).toFixed(1)}% weight)`),
    '',
    'TED-STYLE TALK COACHING (TRANSCRIPT CUES ONLY; DOES NOT AFFECT THE GRADE)',
    ...(coaching.signals || []).map((item) => `${item.detected ? '[Cue found]' : '[Try adding]'} ${item.title}: ${item.detected ? item.evidence : item.suggestion}`),
    '',
    'NEXT STEPS',
    ...recommendations.map((item) => `- ${item}`),
    '',
    coaching.note || 'Talk-structure cues do not verify factual accuracy.'
  ];
  const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${(report.filename || 'presenter-report').replace(/\.[^.]+$/, '')}-report.txt`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function requestLocalJson(url, options) {
  const target = new URL(url, window.location.href);
  if (target.origin !== window.location.origin) {
    throw new Error('Grading requests must stay on this device.');
  }

  const response = await fetch(target, options);
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error('The local grading service returned an invalid response.');
  }

  if (!response.ok) {
    throw new Error(payload.detail || `Local grading failed (${response.status}).`);
  }
  return payload;
}

const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function waitForGrading(jobId, statusUrl) {
  const statusTarget = new URL(statusUrl, window.location.href);
  if (statusTarget.origin !== window.location.origin) {
    throw new Error('Grading status requests must stay on this device.');
  }

  while (true) {
    const job = await requestLocalJson(statusTarget.href);
    if (job.status === 'completed') return job.result;
    if (job.status === 'failed') {
      throw new Error(job.error || 'The local grading job failed.');
    }
    if (job.status === 'not_found') {
      throw new Error(`Local grading job ${jobId} was not found.`);
    }

    $('reportStatus').textContent = job.status === 'running'
      ? 'Analyzing locally…'
      : 'Waiting for local analyzer…';
    await wait(1000);
  }
}

async function checkHealth() {
  try {
    const health = await requestLocalJson('/health');
    if (health.status !== 'ready') throw new Error('Local grading service is not ready.');
    setStatus('Local analysis ready', true);
  } catch {
    setStatus('Local analyzer offline', false);
  }
}

$('videoInput').addEventListener('change', (event) => {
  const count = event.target.files.length;
  $('fileCount').textContent = count ? `${count} video${count === 1 ? '' : 's'} selected` : 'No videos selected';
});

$('uploadForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const files = $('videoInput').files;
  if (!files.length) return;

  const button = $('analyzeButton');
  button.disabled = true;
  button.querySelector('span').textContent = 'Analyzing performance...';
  const speaker = $('speakerName').value || 'Speaker';
  const script = $('scriptInput').value || '';

  try {
    const formData = new FormData();
    Array.from(files).forEach((file) => formData.append('files', file));
    formData.append('speaker', speaker);
    formData.append('script', script);

    const queued = await requestLocalJson('/grade-videos', {
      method: 'POST',
      body: formData
    });
    if (!queued.job_id || !queued.status_url) {
      throw new Error('The local grading service did not return a valid job.');
    }
    const result = await waitForGrading(queued.job_id, queued.status_url);
    if (result.status !== 'success' || !Array.isArray(result.results)) {
      throw new Error('The local grading service did not return any video reports.');
    }

    const reports = result.results;
    const firstReport = renderBatchResults(reports);
    if (!firstReport) {
      const errors = reports
        .filter((report) => report.error)
        .map((report) => `${report.filename || 'Video'}: ${report.error}`);
      throw new Error(errors.length
        ? `No video could be graded:\n${errors.join('\n')}`
        : 'The local grader returned no video reports.');
    }
    renderReport(firstReport, reports.length);
    $('reportStatus').textContent = 'Local video analysis complete';
  } catch (error) {
    $('reportStatus').textContent = 'Local analysis unavailable';
    alert(error.message || 'Unable to analyze the selected videos locally.');
  } finally {
    button.disabled = false;
    button.querySelector('span').textContent = 'Analyze performance';
  }
});

$('feedbackForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector('button');
  const message = $('feedbackMessage');
  const rating = Number(new FormData(event.currentTarget).get('rating'));
  button.disabled = true;
  message.textContent = 'Saving locally...';
  try {
    const note = $('feedbackComment').value.trim();
    const saved = {
      rating,
      comment: note,
      speaker: $('speakerName').value || 'Speaker',
      filename: activeReport?.filename || '',
      score: activeReport?.overview?.overall_score ?? null,
      mode: 'local-demo'
    };
    console.log('Saved local demo feedback', saved);
    message.textContent = 'Thanks, your feedback was saved in demo mode.';
    $('feedbackComment').value = '';
  } catch (error) {
    message.textContent = 'Local demo feedback could not be saved.';
  } finally {
    button.disabled = false;
  }
});

$('downloadReportButton').addEventListener('click', () => {
  if (activeReport) downloadReport(activeReport);
});

document.querySelectorAll('.mobile-nav-item').forEach((button) => {
  button.addEventListener('click', () => {
    const targetId = button.dataset.target;
    const target = targetId ? document.getElementById(targetId) : null;
    if (target) {
      if (targetId === 'resultsPanel' && target.classList.contains('hidden')) {
        target.classList.remove('hidden');
        const emptyState = document.getElementById('emptyState');
        if (emptyState) emptyState.classList.add('hidden');
      }
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    document.querySelectorAll('.mobile-nav-item').forEach((item) => item.classList.toggle('is-active', item === button));
  });
});

checkHealth();
