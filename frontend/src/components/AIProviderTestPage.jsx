import React, { useState } from 'react';
import { getApiUrl } from '../api/config';
import { Activity, Zap, DollarSign, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

const AIProviderTestPage = () => {
  const [loading, setLoading] = useState(false);
  const [testResults, setTestResults] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [costEstimate, setCostEstimate] = useState(null);
  const [generatedQuestion, setGeneratedQuestion] = useState(null);
  const [error, setError] = useState(null);

  const [questionForm, setQuestionForm] = useState({
    subject: 'Matematik',
    topic: 'Parabol',
    difficulty: 'Orta',
    question_type: '',
    force_provider: ''
  });

  const [costForm, setCostForm] = useState({
    subject: 'Matematik',
    num_questions: 1000
  });

  const testProviders = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(getApiUrl('/ai/test-providers/'));
      const data = await response.json();
      setTestResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(getApiUrl('/ai/provider-metrics/'));
      const data = await response.json();
      setMetrics(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getCostEstimate = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(getApiUrl('/ai/cost-estimate/'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(costForm)
      });
      const data = await response.json();
      setCostEstimate(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const generateQuestion = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(getApiUrl('/questions/generate/'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(questionForm)
      });
      const data = await response.json();
      setGeneratedQuestion(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Hybrid AI Provider System Test
          </h1>
          <p className="text-gray-600">
            Test AI providers, generate questions, and view metrics
          </p>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start">
            <AlertCircle className="w-5 h-5 text-red-500 mr-3 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-900">Error</h3>
              <p className="text-red-700">{error}</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Provider Test */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold flex items-center">
                <Activity className="w-5 h-5 mr-2 text-blue-500" />
                Provider Connection Test
              </h2>
              <button
                onClick={testProviders}
                disabled={loading}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
              >
                {loading ? 'Testing...' : 'Test All'}
              </button>
            </div>

            {testResults && (
              <div className="space-y-3">
                {Object.entries(testResults.providers || {}).map(([provider, result]) => (
                  <div key={provider} className="border rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold uppercase">{provider}</span>
                      {result.status === 'connected' ? (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      ) : (
                        <XCircle className="w-5 h-5 text-red-500" />
                      )}
                    </div>
                    <div className="text-sm text-gray-600">
                      <div>Status: {result.status}</div>
                      {result.model && <div>Model: {result.model}</div>}
                      {result.error && <div className="text-red-600">Error: {result.error}</div>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Metrics */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold flex items-center">
                <Zap className="w-5 h-5 mr-2 text-yellow-500" />
                Provider Metrics
              </h2>
              <button
                onClick={getMetrics}
                disabled={loading}
                className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:opacity-50"
              >
                {loading ? 'Loading...' : 'Get Metrics'}
              </button>
            </div>

            {metrics && (
              <div className="space-y-3">
                {metrics.metrics?.map((metric) => (
                  <div key={metric.provider} className="border rounded-lg p-3">
                    <div className="font-semibold uppercase mb-2">{metric.provider}</div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>Success Rate: {metric.success_rate}</div>
                      <div>Avg Time: {metric.avg_response_time}</div>
                      <div>Total Requests: {metric.total_requests}</div>
                      <div>Failed: {metric.failed_requests}</div>
                      <div className="col-span-2 font-semibold text-green-600">
                        Total Cost: {metric.total_cost}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Cost Estimate */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-xl font-semibold flex items-center mb-4">
              <DollarSign className="w-5 h-5 mr-2 text-green-500" />
              Cost Estimate
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Subject</label>
                <select
                  value={costForm.subject}
                  onChange={(e) => setCostForm({ ...costForm, subject: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2"
                >
                  <option>Matematik</option>
                  <option>Geometri</option>
                  <option>Türkçe</option>
                  <option>Fizik</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Number of Questions</label>
                <input
                  type="number"
                  value={costForm.num_questions}
                  onChange={(e) => setCostForm({ ...costForm, num_questions: parseInt(e.target.value) })}
                  className="w-full border rounded-lg px-3 py-2"
                />
              </div>

              <button
                onClick={getCostEstimate}
                disabled={loading}
                className="w-full px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50"
              >
                {loading ? 'Calculating...' : 'Calculate Cost'}
              </button>

              {costEstimate && (
                <div className="border rounded-lg p-4 bg-green-50">
                  <div className="text-lg font-semibold mb-2">
                    Total Cost: {costEstimate.estimate?.total_cost}
                  </div>
                  <div className="text-sm text-gray-600 mb-3">
                    Per Question: {costEstimate.estimate?.cost_per_question}
                  </div>
                  <div className="space-y-2">
                    {Object.entries(costEstimate.estimate?.breakdown || {}).map(([type, data]) => (
                      <div key={type} className="text-sm">
                        <span className="font-medium">{type}:</span> {data.count} × {data.provider} = {data.cost}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Question Generation */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-xl font-semibold mb-4">Generate Question</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Subject</label>
                <input
                  type="text"
                  value={questionForm.subject}
                  onChange={(e) => setQuestionForm({ ...questionForm, subject: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Topic</label>
                <input
                  type="text"
                  value={questionForm.topic}
                  onChange={(e) => setQuestionForm({ ...questionForm, topic: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Difficulty</label>
                <select
                  value={questionForm.difficulty}
                  onChange={(e) => setQuestionForm({ ...questionForm, difficulty: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2"
                >
                  <option>Kolay</option>
                  <option>Orta</option>
                  <option>Zor</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Question Type (Optional)</label>
                <select
                  value={questionForm.question_type}
                  onChange={(e) => setQuestionForm({ ...questionForm, question_type: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2"
                >
                  <option value="">Auto</option>
                  <option value="text">Text Only</option>
                  <option value="parabola">Parabola</option>
                  <option value="geometry">Geometry</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Force Provider (Optional)</label>
                <select
                  value={questionForm.force_provider}
                  onChange={(e) => setQuestionForm({ ...questionForm, force_provider: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2"
                >
                  <option value="">Auto</option>
                  <option value="openai">OpenAI</option>
                  <option value="claude">Claude</option>
                  <option value="deepseek">DeepSeek</option>
                </select>
              </div>

              <button
                onClick={generateQuestion}
                disabled={loading}
                className="w-full px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50"
              >
                {loading ? 'Generating...' : 'Generate Question'}
              </button>

              {generatedQuestion && (
                <div className="border rounded-lg p-4 bg-purple-50 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">Provider: {generatedQuestion.provider}</span>
                    <span className="text-sm text-gray-600">{generatedQuestion.model}</span>
                  </div>
                  
                  <div className="border-t pt-3">
                    <div className="font-medium mb-2">Question:</div>
                    <div className="text-sm">{generatedQuestion.question?.stem}</div>
                  </div>

                  {generatedQuestion.question?.svg && (
                    <div className="border-t pt-3">
                      <div className="font-medium mb-2">SVG:</div>
                      <div dangerouslySetInnerHTML={{ __html: generatedQuestion.question.svg }} />
                    </div>
                  )}

                  <div className="border-t pt-3">
                    <div className="font-medium mb-2">Choices:</div>
                    <div className="space-y-1 text-sm">
                      {Object.entries(generatedQuestion.question?.choices || {}).map(([key, value]) => (
                        <div key={key} className={key === generatedQuestion.question?.answer ? 'font-semibold text-green-600' : ''}>
                          {key}) {value}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="border-t pt-3">
                    <div className="font-medium mb-2">Validation:</div>
                    <div className="text-sm space-y-1">
                      <div>Status: <span className={generatedQuestion.validation?.status === 'passed' ? 'text-green-600' : 'text-red-600'}>
                        {generatedQuestion.validation?.status}
                      </span></div>
                      <div>Score: {generatedQuestion.validation?.score}/100</div>
                      <div>Attempt: {generatedQuestion.validation?.attempt}</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIProviderTestPage;
