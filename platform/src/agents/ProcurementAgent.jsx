import { useState, useEffect, useCallback, useMemo } from 'react';
import { FileText, ChevronDown, ChevronRight, Check, AlertTriangle, AlertCircle, Download, Loader2, RotateCcw, Sparkles, ArrowLeft, ArrowRight, ClipboardList, Settings2, ShieldCheck, Zap } from 'lucide-react';

const API_BASE = `http://${window.location.hostname}:8001`;

// ============================================================
// Demo Data — 一键填充完整演示数据
// ============================================================
const DEMO_PROJECT = {
  name: '集团IT运维服务采购项目',
  method: 'open_bidding',
  budget: '5000000',
  industry: 'IT服务',
  description: '为集团总部及下属单位提供IT基础设施运维服务',
};

const DEMO_PARAMETERS = {
  project_name: '集团IT运维服务采购项目',
  project_code: 'CGZB-2026-IT-001',
  purchaser_name: '某大型集团有限公司',
  purchaser_address: '北京市朝阳区建国路88号',
  agent_name: '中招国际招标有限公司',
  fund_source: '企业自筹',
  scope_description: '为招标人提供IT基础设施运维服务，包括但不限于：服务器运维、网络运维、桌面运维、数据库运维、信息安全运维等。服务范围覆盖集团总部及下属10家分子公司。',
  service_period: '3年（自合同签订之日起）',
  service_location: '北京市（主）及全国各分支机构',
  quality_standard: '符合ITIL v4服务管理框架，SLA可用性≥99.9%',
  qualification_general: '投标人须为依照中国法律登记、注册的具有独立法人资格的企业',
  qualification_cert: '具有ITSS信息技术服务运行维护标准二级及以上资质',
  qualification_finance: '近3年营业收入年均不低于人民币2000万元',
  qualification_performance: '近3年内至少有3个同类IT运维服务项目业绩，单项合同金额不低于200万元',
  qualification_personnel: '拟投入项目经理须具有PMP或ITIL v4认证，驻场团队不少于15人',
  allow_consortium: '不允许',
  allow_subcontract: '不允许',
  max_price: '5000000',
  bid_validity_days: 90,
  deposit_required: '要求',
  deposit_amount: '100000',
  copies_original: 1,
  copies_duplicate: 4,
  electronic_required: '是',
  bid_deadline: '2026-07-15T09:30',
  bid_location: '北京市朝阳区建国路88号A座3层会议室',
  open_location: '北京市朝阳区建国路88号A座3层开标室',
  eval_method: '综合评估法',
  eval_committee_size: 7,
  candidate_count: 3,
  contact_person: '张工',
  contact_phone: '010-85551234',
  contact_email: 'zhangsan@group.com.cn',
};


// ============================================================
// Main Component
// ============================================================
export default function ProcurementAgent({ onBack }) {
  // View mode: 'list' (project list) | 'workflow' (4-step editing)
  const [view, setView] = useState('list');

  // Project list state
  const [projects, setProjects] = useState([]);
  const [loadingProjects, setLoadingProjects] = useState(true);

  // Workflow state
  const [currentStep, setCurrentStep] = useState(1);

  // Step 1: Project info
  const [projectInfo, setProjectInfo] = useState({
    name: '', method: 'open_bidding', budget: '', industry: '', description: '',
  });

  // Step 2: Parameter form
  const [parameterFields, setParameterFields] = useState([]);
  const [parameterGroups, setParameterGroups] = useState([]);
  const [parameters, setParameters] = useState({});
  const [expandedGroups, setExpandedGroups] = useState({});

  // Step 3: Scoring
  const [scoringItems, setScoringItems] = useState({ commercial: [], technical: [] });
  const [scoringPresets, setScoringPresets] = useState({});
  const [selectedCommercial, setSelectedCommercial] = useState([]);
  const [selectedTechnical, setSelectedTechnical] = useState([]);
  const [scoreDistribution, setScoreDistribution] = useState({ commercial: 30, technical: 40, price: 30 });
  const [priceFormulas, setPriceFormulas] = useState({});
  const [selectedFormula, setSelectedFormula] = useState('arithmetic_mean');

  // Step 4: Review & Export
  const [reviewing, setReviewing] = useState(false);
  const [reviewResult, setReviewResult] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [generatedFile, setGeneratedFile] = useState(null);
  const [previewDoc, setPreviewDoc] = useState(null);

  // ── Load projects on mount ──
  useEffect(() => { loadProjects(); }, []);

  // Auto-load preview when entering Step 4
  useEffect(() => {
    if (currentStep === 4 && !previewDoc) {
      previewDocument();
    }
  }, [currentStep]);

  const loadProjects = async () => {
    setLoadingProjects(true);
    try {
      const res = await fetch(`${API_BASE}/api/procurement/projects`);
      const data = await res.json();
      setProjects(data.projects || []);
    } catch (e) { console.error('Load projects failed:', e); }
    finally { setLoadingProjects(false); }
  };

  // ── Load template data (Step 2 & 3) ──
  const loadTemplateData = useCallback(async () => {
    try {
      const [paramsRes, itemsRes, presetsRes, formulasRes] = await Promise.all([
        fetch(`${API_BASE}/api/procurement/templates/parameters`),
        fetch(`${API_BASE}/api/procurement/scoring/items`),
        fetch(`${API_BASE}/api/procurement/scoring/presets`),
        fetch(`${API_BASE}/api/procurement/scoring/formulas`),
      ]);
      const [paramsData, itemsData, presetsData, formulasData] = await Promise.all([
        paramsRes.json(), itemsRes.json(), presetsRes.json(), formulasRes.json(),
      ]);

      setParameterFields(paramsData.fields || []);
      setParameterGroups(paramsData.groups || []);
      setScoringItems(itemsData.items || { commercial: [], technical: [] });
      setScoringPresets(presetsData.presets || {});
      setPriceFormulas(formulasData.formulas || {});

      // Set defaults for parameters
      const defaults = {};
      (paramsData.fields || []).forEach(f => {
        if (f.default !== undefined && f.default !== null) defaults[f.id] = f.default;
      });
      setParameters(prev => ({ ...defaults, ...prev }));

      // Expand first group by default
      if (paramsData.groups?.length) {
        const eg = {};
        paramsData.groups.forEach(g => { eg[g] = true; });
        setExpandedGroups(eg);
      }
    } catch (e) { console.error('Load template data failed:', e); }
  }, []);

  // ── Start workflow ──
  const startNewWorkflow = () => {
    setProjectInfo({ name: '', method: 'open_bidding', budget: '', industry: '', description: '' });
    setParameters({});
    setSelectedCommercial([]);
    setSelectedTechnical([]);
    setScoreDistribution({ commercial: 30, technical: 40, price: 30 });
    setSelectedFormula('arithmetic_mean');
    setReviewResult(null);
    setGeneratedFile(null);
    setPreviewDoc(null);
    setCurrentStep(1);
    setView('workflow');
    loadTemplateData();
  };

  // ── Fill demo data ──
  const fillDemoData = () => {
    setProjectInfo(DEMO_PROJECT);
    setParameters(prev => ({ ...prev, ...DEMO_PARAMETERS }));
  };

  // ── Apply preset ──
  const applyPreset = async (industry) => {
    try {
      const res = await fetch(`${API_BASE}/api/procurement/scoring/presets/${encodeURIComponent(industry)}`);
      const data = await res.json();
      if (data.preset) {
        const p = data.preset;
        setSelectedCommercial(p.commercial_items || []);
        setSelectedTechnical(p.technical_items || []);
        setScoreDistribution(p.score_distribution || { commercial: 30, technical: 40, price: 30 });
        if (p.price_formula) setSelectedFormula(p.price_formula);
      }
    } catch (e) { console.error('Apply preset failed:', e); }
  };

  // ── Build scoring criteria ──
  const buildScoringCriteria = () => ({
    commercial_items: selectedCommercial,
    technical_items: selectedTechnical,
    score_distribution: scoreDistribution,
    price_formula: selectedFormula,
  });

  // ── Run AI review ──
  const runReview = async () => {
    setReviewing(true);
    setReviewResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/procurement/documents/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          parameters: { ...parameters, ...projectInfo },
          scoring_criteria: buildScoringCriteria(),
        }),
      });
      const data = await res.json();
      setReviewResult(data);
    } catch (e) {
      console.error('Review failed:', e);
      setReviewResult({ error: e.message });
    } finally { setReviewing(false); }
  };

  // ── Generate Word document ──
  const generateDocument = async () => {
    setGenerating(true);
    setGeneratedFile(null);
    try {
      const res = await fetch(`${API_BASE}/api/procurement/documents/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          parameters: { ...parameters, ...projectInfo },
          scoring_criteria: buildScoringCriteria(),
        }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        setGeneratedFile(data);
      }
    } catch (e) {
      console.error('Generate failed:', e);
    } finally { setGenerating(false); }
  };

  // ── Preview document ──
  const previewDocument = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/procurement/templates/fill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          parameters: { ...parameters, ...projectInfo },
          scoring_criteria: buildScoringCriteria(),
        }),
      });
      const data = await res.json();
      setPreviewDoc(data.document || null);
    } catch (e) { console.error('Preview failed:', e); }
  };

  // ── Download file ──
  const downloadFile = () => {
    if (!generatedFile?.file_name) return;
    const url = `${API_BASE}/api/procurement/documents/download/${generatedFile.file_name}`;
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', generatedFile.file_name);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // ── Method labels ──
  const methodLabels = {
    open_bidding: '公开招标', negotiation: '竞争性磋商', competitive_talk: '竞争性谈判',
    inquiry: '询价', sole_source: '单一来源', framework: '框架协议',
  };

  const statusLabels = {
    draft: { text: '草稿', cls: 'bg-zinc-700/50 text-zinc-300' },
    reviewing: { text: '审核中', cls: 'bg-blue-500/20 text-blue-400' },
    published: { text: '已发布', cls: 'bg-emerald-500/20 text-emerald-400' },
    evaluating: { text: '评审中', cls: 'bg-amber-500/20 text-amber-400' },
    completed: { text: '已完成', cls: 'bg-emerald-500/20 text-emerald-300' },
  };

  // ── Steps config ──
  const steps = [
    { num: 1, label: '项目信息', icon: <ClipboardList size={14} /> },
    { num: 2, label: '参数填充', icon: <Settings2 size={14} /> },
    { num: 3, label: '评分配置', icon: <Sparkles size={14} /> },
    { num: 4, label: '审核输出', icon: <ShieldCheck size={14} /> },
  ];

  // Check if can proceed to next step
  const canProceed = (step) => {
    if (step === 1) return projectInfo.name.trim().length > 0;
    if (step === 2) return parameters.project_name && parameters.purchaser_name;
    if (step === 3) return selectedCommercial.length > 0 || selectedTechnical.length > 0;
    return true;
  };

  // ================================================================
  // RENDER
  // ================================================================
  return (
    <div className="h-full flex flex-col bg-zinc-950">
      {/* ── Header ── */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-zinc-800 bg-zinc-900/80 backdrop-blur shrink-0">
        <div className="flex items-center space-x-2">
          <button
            onClick={() => view === 'workflow' ? setView('list') : onBack?.()}
            className="text-zinc-500 hover:text-zinc-300 transition-colors p-1 rounded hover:bg-zinc-800"
            title="返回"
          >
            <ArrowLeft size={16} />
          </button>
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <FileText size={14} className="text-white" />
          </div>
          <div>
            <h1 className="text-[13px] font-bold text-zinc-100">智能采购文件编制</h1>
            <p className="text-[9px] text-zinc-500 uppercase tracking-widest">
              {view === 'list' ? '项目列表' : `步骤 ${currentStep}/4 · ${steps[currentStep - 1]?.label}`}
            </p>
          </div>
        </div>
        {view === 'workflow' && (
          <button onClick={() => { setView('list'); loadProjects(); }}
            className="text-zinc-500 hover:text-zinc-300 transition-colors p-1.5 rounded hover:bg-zinc-800" title="返回列表">
            <RotateCcw size={14} />
          </button>
        )}
      </div>

      {/* ── Step Bar (workflow mode) ── */}
      {view === 'workflow' && (
        <div className="flex items-center px-4 py-2 border-b border-zinc-800 bg-zinc-900/60 gap-1">
          {steps.map((step, i) => {
            const isActive = step.num === currentStep;
            const isDone = step.num < currentStep;
            return (
              <div key={step.num} className="flex items-center gap-1">
                <button
                  onClick={() => isDone && setCurrentStep(step.num)}
                  disabled={!isDone && !isActive}
                  className={`flex items-center gap-1.5 text-[10px] px-2.5 py-1.5 rounded-md transition-all ${
                    isActive
                      ? 'bg-blue-500/20 border border-blue-500/40 text-blue-300 font-bold'
                      : isDone
                        ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 cursor-pointer hover:bg-emerald-500/20'
                        : 'bg-zinc-800/50 border border-zinc-700/50 text-zinc-600'
                  }`}
                >
                  {isDone ? <Check size={11} /> : step.icon}
                  <span>{step.label}</span>
                </button>
                {i < steps.length - 1 && (
                  <div className={`w-6 h-px ${isDone ? 'bg-emerald-500/40' : 'bg-zinc-700'}`} />
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── Main Content ── */}
      <div className="flex-1 overflow-y-auto">
        {view === 'list' ? renderProjectList() : renderWorkflow()}
      </div>

      {/* ── Bottom Navigation (workflow mode) ── */}
      {view === 'workflow' && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-zinc-800 bg-zinc-900/80 backdrop-blur shrink-0">
          <button
            onClick={() => currentStep > 1 ? setCurrentStep(currentStep - 1) : setView('list')}
            className="flex items-center gap-1 text-[11px] text-zinc-400 hover:text-zinc-200 transition-colors px-3 py-1.5 rounded-md hover:bg-zinc-800"
          >
            <ArrowLeft size={12} />
            <span>{currentStep === 1 ? '返回列表' : '上一步'}</span>
          </button>

          <div className="flex items-center gap-2">
            {currentStep === 1 && (
              <button
                onClick={fillDemoData}
                className="flex items-center gap-1 text-[11px] text-amber-400 hover:text-amber-300 transition-colors px-3 py-1.5 rounded-md hover:bg-amber-500/10 border border-amber-500/30"
              >
                <Zap size={12} />
                <span>Demo数据</span>
              </button>
            )}
            {currentStep < 4 ? (
              <button
                onClick={() => {
                  if (currentStep === 2) {
                    // Sync project info to parameters
                    setParameters(prev => ({
                      ...prev,
                      project_name: prev.project_name || projectInfo.name,
                      purchaser_name: prev.purchaser_name || '',
                    }));
                  }
                  setCurrentStep(currentStep + 1);
                  if (currentStep === 3) previewDocument();
                }}
                disabled={!canProceed(currentStep)}
                className={`flex items-center gap-1 text-[11px] px-4 py-1.5 rounded-md transition-all font-bold ${
                  canProceed(currentStep)
                    ? 'bg-blue-600 text-white hover:bg-blue-500 shadow-lg shadow-blue-500/20'
                    : 'bg-zinc-700 text-zinc-500 cursor-not-allowed'
                }`}
              >
                <span>下一步</span>
                <ArrowRight size={12} />
              </button>
            ) : (
              <button
                onClick={generateDocument}
                disabled={generating}
                className="flex items-center gap-1 text-[11px] px-4 py-1.5 rounded-md bg-emerald-600 text-white hover:bg-emerald-500 shadow-lg shadow-emerald-500/20 font-bold transition-all"
              >
                {generating ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
                <span>{generating ? '生成中...' : '生成Word文档'}</span>
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );

  // ================================================================
  // Render: Project List
  // ================================================================
  function renderProjectList() {
    return (
      <div className="p-4 space-y-4">
        {/* Action bar */}
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-zinc-200">采购项目</h2>
          <button
            onClick={startNewWorkflow}
            className="flex items-center gap-1.5 text-[11px] px-3 py-1.5 rounded-md bg-blue-600 text-white hover:bg-blue-500 transition-colors font-bold shadow-lg shadow-blue-500/20"
          >
            <Sparkles size={12} />
            <span>新建采购文件</span>
          </button>
        </div>

        {/* List */}
        {loadingProjects ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 size={20} className="animate-spin text-zinc-500" />
          </div>
        ) : projects.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-14 h-14 bg-zinc-800 rounded-2xl flex items-center justify-center mx-auto mb-3">
              <FileText size={24} className="text-zinc-600" />
            </div>
            <p className="text-zinc-500 text-sm">暂无采购项目</p>
            <p className="text-zinc-600 text-xs mt-1">点击「新建采购文件」开始编制</p>
          </div>
        ) : (
          <div className="space-y-2">
            {projects.map(p => {
              const st = statusLabels[p.status] || statusLabels.draft;
              return (
                <div key={p.id}
                  className="bg-zinc-900/80 rounded-lg border border-zinc-800 p-3.5 hover:border-zinc-600 transition-all cursor-pointer group"
                  onClick={() => { /* TODO: open existing project */ }}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-[13px] font-semibold text-zinc-200 group-hover:text-zinc-100">{p.name}</h3>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-[10px] text-zinc-500">{methodLabels[p.method] || p.method}</span>
                        {p.budget > 0 && <span className="text-[10px] text-zinc-500">¥{Number(p.budget).toLocaleString()}</span>}
                        <span className="text-[10px] text-zinc-600">{p.created_at?.split('T')[0]}</span>
                      </div>
                    </div>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full ${st.cls}`}>{st.text}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // ================================================================
  // Render: Workflow
  // ================================================================
  function renderWorkflow() {
    return (
      <div className="p-4">
        {currentStep === 1 && renderStep1()}
        {currentStep === 2 && renderStep2()}
        {currentStep === 3 && renderStep3()}
        {currentStep === 4 && renderStep4()}
      </div>
    );
  }

  // ── Step 1: Project Info ──
  function renderStep1() {
    return (
      <div className="max-w-2xl mx-auto space-y-5">
        <div>
          <h2 className="text-sm font-bold text-zinc-200 mb-1">项目基本信息</h2>
          <p className="text-[11px] text-zinc-500">填写采购项目的基本信息，或点击右下角「Demo数据」快速体验。</p>
        </div>

        <div className="space-y-3">
          <FormField label="项目名称" required>
            <input
              value={projectInfo.name}
              onChange={e => setProjectInfo(p => ({ ...p, name: e.target.value }))}
              className="form-input" placeholder="如：集团IT运维服务采购项目"
            />
          </FormField>

          <div className="grid grid-cols-2 gap-3">
            <FormField label="采购方式">
              <select
                value={projectInfo.method}
                onChange={e => setProjectInfo(p => ({ ...p, method: e.target.value }))}
                className="form-input"
              >
                {Object.entries(methodLabels).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </FormField>
            <FormField label="预算金额（元）">
              <input
                type="number" value={projectInfo.budget}
                onChange={e => setProjectInfo(p => ({ ...p, budget: e.target.value }))}
                className="form-input" placeholder="0"
              />
            </FormField>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <FormField label="行业领域">
              <select
                value={projectInfo.industry}
                onChange={e => setProjectInfo(p => ({ ...p, industry: e.target.value }))}
                className="form-input"
              >
                <option value="">选择行业</option>
                <option value="IT服务">IT服务</option>
                <option value="工程项目">工程项目</option>
                <option value="通用服务">通用服务</option>
                <option value="咨询服务">咨询服务</option>
                <option value="物资采购">物资采购</option>
              </select>
            </FormField>
            <FormField label="项目简述">
              <input
                value={projectInfo.description}
                onChange={e => setProjectInfo(p => ({ ...p, description: e.target.value }))}
                className="form-input" placeholder="一句话描述"
              />
            </FormField>
          </div>
        </div>

        {/* Quick preview card */}
        {projectInfo.name && (
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-3 mt-4">
            <div className="text-[10px] text-zinc-500 mb-1">预览</div>
            <div className="text-[12px] text-zinc-200 font-semibold">{projectInfo.name}</div>
            <div className="flex gap-3 mt-1">
              <span className="text-[10px] text-blue-400">{methodLabels[projectInfo.method]}</span>
              {projectInfo.budget && <span className="text-[10px] text-zinc-400">¥{Number(projectInfo.budget).toLocaleString()}</span>}
              {projectInfo.industry && <span className="text-[10px] text-zinc-400">{projectInfo.industry}</span>}
            </div>
          </div>
        )}
      </div>
    );
  }

  // ── Step 2: Parameter Form ──
  function renderStep2() {
    const grouped = {};
    parameterGroups.forEach(g => { grouped[g] = []; });
    parameterFields.forEach(f => {
      if (!grouped[f.group]) grouped[f.group] = [];
      grouped[f.group].push(f);
    });

    return (
      <div className="max-w-2xl mx-auto space-y-3">
        <div>
          <h2 className="text-sm font-bold text-zinc-200 mb-1">须知前附表参数</h2>
          <p className="text-[11px] text-zinc-500">
            共 {parameterFields.length} 个字段，{parameterGroups.length} 个分组。灰色为默认值，可直接修改。
          </p>
        </div>

        {parameterGroups.map(group => {
          const fields = grouped[group] || [];
          const isExpanded = expandedGroups[group] !== false;
          const filledCount = fields.filter(f => parameters[f.id] && String(parameters[f.id]).trim()).length;

          return (
            <div key={group} className="bg-zinc-900/60 border border-zinc-800 rounded-lg overflow-hidden">
              <button
                onClick={() => setExpandedGroups(eg => ({ ...eg, [group]: !isExpanded }))}
                className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-zinc-800/50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  {isExpanded ? <ChevronDown size={12} className="text-zinc-500" /> : <ChevronRight size={12} className="text-zinc-500" />}
                  <span className="text-[12px] font-semibold text-zinc-300">{group}</span>
                </div>
                <span className="text-[10px] text-zinc-500">{filledCount}/{fields.length}</span>
              </button>

              {isExpanded && (
                <div className="px-3 pb-3 space-y-2 border-t border-zinc-800/50">
                  {fields.map(field => (
                    <div key={field.id} className="mt-2">
                      <label className="text-[10px] text-zinc-500 block mb-0.5">
                        {field.label} {field.required && <span className="text-red-400">*</span>}
                      </label>
                      {field.type === 'select' ? (
                        <select
                          value={parameters[field.id] || field.default || ''}
                          onChange={e => setParameters(p => ({ ...p, [field.id]: e.target.value }))}
                          className="form-input text-[11px]"
                        >
                          {(field.options || []).map(o => <option key={o} value={o}>{o}</option>)}
                        </select>
                      ) : field.type === 'textarea' ? (
                        <textarea
                          value={parameters[field.id] || ''}
                          onChange={e => setParameters(p => ({ ...p, [field.id]: e.target.value }))}
                          className="form-input text-[11px] min-h-[60px] resize-y"
                          placeholder={field.default || ''}
                          rows={2}
                        />
                      ) : field.type === 'datetime' ? (
                        <input
                          type="datetime-local"
                          value={parameters[field.id] || ''}
                          onChange={e => setParameters(p => ({ ...p, [field.id]: e.target.value }))}
                          className="form-input text-[11px]"
                        />
                      ) : (
                        <input
                          type={field.type === 'number' ? 'number' : 'text'}
                          value={parameters[field.id] ?? ''}
                          onChange={e => setParameters(p => ({ ...p, [field.id]: field.type === 'number' ? (e.target.value === '' ? '' : Number(e.target.value)) : e.target.value }))}
                          className="form-input text-[11px]"
                          placeholder={field.default !== undefined ? String(field.default) : ''}
                        />
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  // ── Step 3: Scoring Config ──
  function renderStep3() {
    const totalScore = (scoreDistribution.commercial || 0) + (scoreDistribution.technical || 0) + (scoreDistribution.price || 0);
    const commercialItemScore = selectedCommercial.reduce((sum, id) => {
      const item = scoringItems.commercial?.find(i => i.id === id);
      return sum + (item?.default_score || 0);
    }, 0);
    const technicalItemScore = selectedTechnical.reduce((sum, id) => {
      const item = scoringItems.technical?.find(i => i.id === id);
      return sum + (item?.default_score || 0);
    }, 0);

    return (
      <div className="max-w-3xl mx-auto space-y-4">
        <div>
          <h2 className="text-sm font-bold text-zinc-200 mb-1">评分标准配置</h2>
          <p className="text-[11px] text-zinc-500">配置商务、技术、价格评分项及分值分配。可使用行业预设快速加载。</p>
        </div>

        {/* Presets */}
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-3">
          <div className="text-[10px] text-zinc-500 mb-2">行业预设方案</div>
          <div className="flex gap-2 flex-wrap">
            {Object.entries(scoringPresets).map(([key, val]) => (
              <button
                key={key}
                onClick={() => applyPreset(key)}
                className="text-[11px] px-3 py-1.5 rounded-md border border-zinc-700 text-zinc-300 hover:border-blue-500/50 hover:text-blue-300 hover:bg-blue-500/10 transition-all"
              >
                <Zap size={10} className="inline mr-1" />
                {key}
              </button>
            ))}
          </div>
        </div>

        {/* Score Distribution */}
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-3">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[10px] text-zinc-500">分值构成 (总分 {totalScore})</span>
            {totalScore !== 100 && (
              <span className="text-[10px] text-red-400 flex items-center gap-1">
                <AlertTriangle size={10} /> 总分应为100
              </span>
            )}
          </div>
          <div className="grid grid-cols-3 gap-3">
            {[
              { key: 'commercial', label: '商务分', color: 'bg-blue-500' },
              { key: 'technical', label: '技术分', color: 'bg-emerald-500' },
              { key: 'price', label: '价格分', color: 'bg-amber-500' },
            ].map(item => (
              <div key={item.key} className="text-center">
                <div className="text-[10px] text-zinc-500 mb-1">{item.label}</div>
                <input
                  type="number" min="0" max="100"
                  value={scoreDistribution[item.key] || 0}
                  onChange={e => setScoreDistribution(d => ({ ...d, [item.key]: parseInt(e.target.value) || 0 }))}
                  className="w-16 text-center form-input text-[13px] font-bold mx-auto"
                />
                <div className={`h-1 ${item.color} rounded-full mt-1.5 mx-auto transition-all`}
                  style={{ width: `${Math.min(100, (scoreDistribution[item.key] || 0))}%` }} />
              </div>
            ))}
          </div>
        </div>

        {/* Commercial Scoring Items */}
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-blue-400">商务评分项</span>
            <span className="text-[10px] text-zinc-500">
              已选 {selectedCommercial.length} 项 · 子项合计 {commercialItemScore} 分
            </span>
          </div>
          <div className="space-y-1.5">
            {(scoringItems.commercial || []).map(item => {
              const checked = selectedCommercial.includes(item.id);
              return (
                <label key={item.id}
                  className={`flex items-start gap-2 p-2 rounded-md cursor-pointer transition-all ${
                    checked ? 'bg-blue-500/10 border border-blue-500/30' : 'bg-zinc-800/30 border border-transparent hover:bg-zinc-800/60'
                  }`}
                >
                  <input
                    type="checkbox" checked={checked}
                    onChange={e => {
                      if (e.target.checked) setSelectedCommercial(s => [...s, item.id]);
                      else setSelectedCommercial(s => s.filter(i => i !== item.id));
                    }}
                    className="mt-0.5 accent-blue-500"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-semibold text-zinc-200">{item.name}</span>
                      <span className="text-[10px] text-blue-400 font-bold">{item.default_score}分</span>
                    </div>
                    <p className="text-[10px] text-zinc-500 mt-0.5 leading-relaxed">{item.description}</p>
                  </div>
                </label>
              );
            })}
          </div>
        </div>

        {/* Technical Scoring Items */}
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-emerald-400">技术评分项</span>
            <span className="text-[10px] text-zinc-500">
              已选 {selectedTechnical.length} 项 · 子项合计 {technicalItemScore} 分
            </span>
          </div>
          <div className="space-y-1.5">
            {(scoringItems.technical || []).map(item => {
              const checked = selectedTechnical.includes(item.id);
              return (
                <label key={item.id}
                  className={`flex items-start gap-2 p-2 rounded-md cursor-pointer transition-all ${
                    checked ? 'bg-emerald-500/10 border border-emerald-500/30' : 'bg-zinc-800/30 border border-transparent hover:bg-zinc-800/60'
                  }`}
                >
                  <input
                    type="checkbox" checked={checked}
                    onChange={e => {
                      if (e.target.checked) setSelectedTechnical(s => [...s, item.id]);
                      else setSelectedTechnical(s => s.filter(i => i !== item.id));
                    }}
                    className="mt-0.5 accent-emerald-500"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-semibold text-zinc-200">{item.name}</span>
                      <span className="text-[10px] text-emerald-400 font-bold">{item.default_score}分</span>
                    </div>
                    <p className="text-[10px] text-zinc-500 mt-0.5 leading-relaxed">{item.description}</p>
                  </div>
                </label>
              );
            })}
          </div>
        </div>

        {/* Price Formula */}
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-3">
          <div className="text-[11px] font-semibold text-amber-400 mb-2">价格评分公式</div>
          <div className="space-y-1.5">
            {Object.entries(priceFormulas).map(([key, formula]) => (
              <label key={key}
                className={`flex items-start gap-2 p-2 rounded-md cursor-pointer transition-all ${
                  selectedFormula === key ? 'bg-amber-500/10 border border-amber-500/30' : 'bg-zinc-800/30 border border-transparent hover:bg-zinc-800/60'
                }`}
              >
                <input
                  type="radio" name="priceFormula" checked={selectedFormula === key}
                  onChange={() => setSelectedFormula(key)}
                  className="mt-0.5 accent-amber-500"
                />
                <div className="flex-1">
                  <span className="text-[11px] font-semibold text-zinc-200">{formula.name}</span>
                  <p className="text-[10px] text-zinc-500 mt-0.5">{formula.description}</p>
                  <code className="text-[9px] text-amber-400/60 mt-0.5 block">{formula.formula}</code>
                </div>
              </label>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ── Step 4: Review & Export ──
  function renderStep4() {
    return (
      <div className="max-w-3xl mx-auto space-y-4">
        <div>
          <h2 className="text-sm font-bold text-zinc-200 mb-1">审核与输出</h2>
          <p className="text-[11px] text-zinc-500">预览文档结构，运行AI智能审核，生成并下载Word文件。</p>
        </div>

        {/* Document Preview */}
        {!previewDoc && (
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-6 text-center">
            <Loader2 size={20} className="animate-spin text-blue-400 mx-auto mb-2" />
            <div className="text-[11px] text-zinc-500">正在加载文档预览...</div>
          </div>
        )}
        {previewDoc && (() => {
          const chapters = previewDoc.chapters || [];
          const totalChars = chapters.reduce((sum, ch) => sum + (ch.content?.length || 0), 0);
          const filledCount = chapters.filter(ch => ch.content && ch.content.length > 0).length;
          return (
            <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-3">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <FileText size={14} className="text-violet-400" />
                  <span className="text-[11px] font-semibold text-zinc-200">文档预览</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[10px] text-zinc-500">共 {chapters.length} 章</span>
                  <span className="text-[10px] text-zinc-500">约 {(totalChars / 1000).toFixed(1)}K 字</span>
                  <span className="text-[10px] text-emerald-400">{filledCount}/{chapters.length} 已填充</span>
                  <button onClick={previewDocument} className="text-[9px] text-blue-400 hover:text-blue-300 flex items-center gap-0.5">
                    <RotateCcw size={9} /> 刷新
                  </button>
                </div>
              </div>
              <div className="space-y-1">
                {chapters.map((ch, i) => (
                  <ChapterPreview key={i} chapter={ch} index={i} />
                ))}
              </div>
              {previewDoc.metadata && (
                <div className="mt-3 pt-2 border-t border-zinc-800/50">
                  <div className="flex flex-wrap gap-x-4 gap-y-1">
                    <span className="text-[10px] text-zinc-500">📌 {previewDoc.metadata.project_name}</span>
                    <span className="text-[10px] text-zinc-500">🏢 {previewDoc.metadata.purchaser_name}</span>
                    <span className="text-[10px] text-zinc-500">📊 {previewDoc.metadata.eval_method}</span>
                  </div>
                </div>
              )}
            </div>
          );
        })()}

        {/* AI Review */}
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-3">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <ShieldCheck size={14} className="text-blue-400" />
              <span className="text-[11px] font-semibold text-zinc-200">AI 智能审核</span>
            </div>
            <button
              onClick={runReview}
              disabled={reviewing}
              className={`flex items-center gap-1 text-[10px] px-3 py-1.5 rounded-md transition-all font-bold ${
                reviewing
                  ? 'bg-zinc-700 text-zinc-400 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-500'
              }`}
            >
              {reviewing ? <Loader2 size={10} className="animate-spin" /> : <Sparkles size={10} />}
              <span>{reviewing ? '审核中...' : '运行审核'}</span>
            </button>
          </div>

          {reviewResult && !reviewResult.error && (
            <div className="space-y-2">
              {/* 3-dimension review cards */}
              <div className="grid grid-cols-3 gap-2">
                {[
                  { key: 'compliance', label: '合规性', icon: <ShieldCheck size={16} />, color: 'blue' },
                  { key: 'logic', label: '逻辑性', icon: <AlertTriangle size={16} />, color: 'amber' },
                  { key: 'accuracy', label: '准确性', icon: <AlertCircle size={16} />, color: 'emerald' },
                ].map(dim => {
                  const result = reviewResult[dim.key] || reviewResult.dimensions?.[dim.key] || {};
                  const passed = result.passed !== false && result.status !== 'fail';
                  const issues = result.issues || result.findings || [];
                  return (
                    <div key={dim.key}
                      className={`rounded-lg border p-2.5 ${
                        passed
                          ? `bg-${dim.color}-500/5 border-${dim.color}-500/20`
                          : 'bg-red-500/5 border-red-500/20'
                      }`}
                    >
                      <div className="flex items-center gap-1.5 mb-1">
                        <span className={passed ? `text-${dim.color}-400` : 'text-red-400'}>{dim.icon}</span>
                        <span className="text-[11px] font-semibold text-zinc-200">{dim.label}</span>
                      </div>
                      <div className={`text-[10px] font-bold ${passed ? 'text-emerald-400' : 'text-red-400'}`}>
                        {passed ? '✅ 通过' : `⚠️ ${issues.length} 个问题`}
                      </div>
                      {issues.length > 0 && (
                        <div className="mt-1.5 space-y-0.5">
                          {issues.slice(0, 3).map((issue, i) => (
                            <div key={i} className="text-[9px] text-zinc-400">• {typeof issue === 'string' ? issue : issue.message || issue.description || JSON.stringify(issue)}</div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Text report */}
              {reviewResult.text_report && (
                <details className="mt-2">
                  <summary className="text-[10px] text-zinc-500 cursor-pointer hover:text-zinc-300">
                    📋 查看完整审核报告
                  </summary>
                  <pre className="mt-2 text-[10px] text-zinc-400 whitespace-pre-wrap bg-zinc-800/50 rounded-md p-3 max-h-60 overflow-y-auto border border-zinc-700/50">
                    {reviewResult.text_report}
                  </pre>
                </details>
              )}

              {/* Summary */}
              {reviewResult.summary && (
                <div className="text-[10px] text-zinc-400 mt-2 bg-zinc-800/30 rounded p-2">
                  {reviewResult.summary}
                </div>
              )}
            </div>
          )}

          {reviewResult?.error && (
            <div className="text-[11px] text-red-400 bg-red-500/10 rounded-md p-2">
              ❌ 审核失败: {reviewResult.error}
            </div>
          )}

          {!reviewResult && !reviewing && (
            <div className="text-[10px] text-zinc-600 py-4 text-center">
              点击「运行审核」进行合规性、逻辑性、准确性三维检查
            </div>
          )}
        </div>

        {/* Generated File */}
        {generatedFile && (
          <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Check size={16} className="text-emerald-400" />
                <div>
                  <div className="text-[11px] font-bold text-emerald-300">文档生成成功</div>
                  <div className="text-[10px] text-zinc-400">{generatedFile.file_name}</div>
                </div>
              </div>
              <button
                onClick={downloadFile}
                className="flex items-center gap-1 text-[11px] px-3 py-1.5 rounded-md bg-emerald-600 text-white hover:bg-emerald-500 font-bold transition-all"
              >
                <Download size={12} />
                <span>下载</span>
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }
}


// ============================================================
// Shared Components
// ============================================================
function FormField({ label, required, children }) {
  return (
    <div>
      <label className="text-[10px] text-zinc-500 block mb-1">
        {label} {required && <span className="text-red-400">*</span>}
      </label>
      {children}
    </div>
  );
}

function ChapterPreview({ chapter, index }) {
  const [expanded, setExpanded] = useState(false);
  const content = chapter.content || '';
  const charCount = content.length;
  const hasContent = charCount > 0;
  const lineCount = content ? content.split('\n').filter(l => l.trim()).length : 0;

  const statusColor = hasContent
    ? charCount > 1000 ? 'text-emerald-400' : 'text-amber-400'
    : 'text-zinc-600';

  return (
    <div className="border border-zinc-800/50 rounded-md overflow-hidden">
      <button
        onClick={() => hasContent && setExpanded(!expanded)}
        className={`w-full flex items-center gap-2 px-2.5 py-1.5 text-left transition-all ${
          hasContent ? 'hover:bg-zinc-800/40 cursor-pointer' : 'cursor-default opacity-60'
        } ${expanded ? 'bg-zinc-800/30' : ''}`}
      >
        {hasContent ? (
          expanded ? <ChevronDown size={10} className="text-zinc-500 shrink-0" /> : <ChevronRight size={10} className="text-zinc-500 shrink-0" />
        ) : (
          <span className="w-2.5 shrink-0" />
        )}
        <span className="text-[11px] text-zinc-300 font-medium flex-1">{chapter.title}</span>
        <span className={`text-[9px] ${statusColor} font-mono`}>
          {hasContent ? `${charCount} 字 · ${lineCount} 行` : '空'}
        </span>
      </button>
      {expanded && hasContent && (
        <div className="px-3 pb-2.5 border-t border-zinc-800/30">
          <pre className="text-[10px] text-zinc-400 whitespace-pre-wrap mt-2 max-h-48 overflow-y-auto leading-relaxed font-sans">
            {content.length > 2000 ? content.slice(0, 2000) + '\n\n... (内容较长，已截取前 2000 字)' : content}
          </pre>
        </div>
      )}
    </div>
  );
}
