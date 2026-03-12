import { useState, useRef, useEffect, useMemo } from 'react';
import { FileText, Send, Loader2, CheckCircle, Building2, User, Phone, Mail, DollarSign, Calendar, MapPin, ClipboardList, Download, RotateCcw, Upload, Sparkles, AlertTriangle, ChevronRight, Eye, Copy, FileDown, CheckSquare, XCircle, Shield, BarChart3 } from 'lucide-react';
import { marked } from 'marked';

const API_BASE = 'http://localhost:8000';

marked.setOptions({ breaks: true, gfm: true });

// ── Word 级排版 CSS (保留原有样式) ──
const WORD_STYLES = `
.bidding-doc { font-family: "SimSun", "宋体", "Songti SC", serif; font-size: 14px; line-height: 1.8; color: #1a1a1a; }
.bidding-doc h1 { font-family: "SimHei", "黑体", "Heiti SC", sans-serif; font-size: 22px; font-weight: bold; text-align: center; margin: 32px 0 20px; padding-bottom: 8px; border-bottom: 2px solid #c00; }
.bidding-doc h2 { font-family: "SimHei", "黑体", "Heiti SC", sans-serif; font-size: 17px; font-weight: bold; margin: 24px 0 12px; padding-left: 10px; border-left: 4px solid #c00; }
.bidding-doc h3 { font-family: "SimHei", "黑体", "Heiti SC", sans-serif; font-size: 15px; font-weight: bold; margin: 18px 0 8px; }
.bidding-doc h4 { font-size: 14px; font-weight: bold; margin: 14px 0 6px; }
.bidding-doc p { margin: 6px 0; text-indent: 2em; text-align: justify; }
.bidding-doc ul, .bidding-doc ol { margin: 8px 0 8px 2em; }
.bidding-doc li { margin: 3px 0; text-indent: 0; }
.bidding-doc strong { color: #b00; }
.bidding-doc table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }
.bidding-doc th { background: #f5f0e8; font-weight: bold; text-align: center; }
.bidding-doc th, .bidding-doc td { border: 1px solid #999; padding: 6px 10px; text-align: left; }
.bidding-doc hr { border: none; border-top: 1px solid #ccc; margin: 20px 0; }
.bidding-doc blockquote { border-left: 4px solid #ddd; padding-left: 12px; color: #666; margin: 10px 0; font-style: italic; }
.bidding-doc code { background: #f5f5f5; padding: 1px 4px; border-radius: 2px; font-size: 12px; }
`;

export default function BiddingAgent() {
    // Steps: 1=上传 2=解析中 3=确认结构 4=生成中 5=完成(校验+下载)
    const [step, setStep] = useState(1);
    const [file, setFile] = useState(null);
    const [parsing, setParsing] = useState(false);

    // Task state from backend
    const [taskId, setTaskId] = useState(null);
    const [requirements, setRequirements] = useState(null);
    const [rawSectionsCount, setRawSectionsCount] = useState(0);

    // Company info form
    const [companyData, setCompanyData] = useState({
        company_name: '', legal_rep: '', license_no: '', address: '',
        phone: '', email: '', established_year: '', lawyer_count: '',
        partner_count: '', registered_capital: '',
    });

    // Generation progress
    const [genProgress, setGenProgress] = useState({ current: 0, total: 0, sections: [], llmCount: 0, codeCount: 0 });
    const [generating, setGenerating] = useState(false);
    const [matchedTemplate, setMatchedTemplate] = useState(null);

    // Results
    const [verification, setVerification] = useState(null);
    const [outputFilename, setOutputFilename] = useState('');
    const [elapsed, setElapsed] = useState(0);

    const fileInputRef = useRef(null);
    const timerRef = useRef(null);
    const abortRef = useRef(null);

    const updateCompany = (k, v) => setCompanyData(prev => ({ ...prev, [k]: v }));

    // ── Demo 数据 ──
    const fillDemo = () => {
        setCompanyData({
            company_name: '湖南天衡律师事务所',
            legal_rep: '张建明',
            license_no: '湘司律字第0088号',
            address: '湖南省长沙市岳麓区潇湘中路328号',
            phone: '0731-88886666',
            email: 'contact@tianheng-law.com',
            established_year: '2003',
            lawyer_count: '50',
            partner_count: '12',
            registered_capital: '500万元',
        });
    };

    // ── Step 1 → 2: 上传招标文件 ──
    const handleFileSelect = (e) => {
        const f = e.target.files[0];
        if (f) setFile(f);
    };

    const handleUploadAndParse = async () => {
        if (!file) return;
        setStep(2);
        setParsing(true);
        const startTime = Date.now();
        timerRef.current = setInterval(() => setElapsed((Date.now() - startTime) / 1000), 100);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const res = await fetch(`${API_BASE}/api/bidding/parse-structure`, {
                method: 'POST',
                body: formData,
            });
            const result = await res.json();

            if (result.success && result.data) {
                setTaskId(result.data.task_id);
                setRequirements(result.data.requirements);
                setRawSectionsCount(result.data.raw_sections_count);
                setStep(3);
            } else {
                alert('解析失败: ' + (result.message || '未知错误'));
                setStep(1);
            }
        } catch (err) {
            alert('上传失败: ' + err.message);
            setStep(1);
        } finally {
            setParsing(false);
            clearInterval(timerRef.current);
        }
    };

    // ── Step 3 → 4: 开始生成 ──
    const startGeneration = async () => {
        if (!taskId) return;
        setStep(4);
        setGenerating(true);
        setGenProgress({ current: 0, total: 0, sections: [] });
        setVerification(null);
        const startTime = Date.now();
        timerRef.current = setInterval(() => setElapsed((Date.now() - startTime) / 1000), 100);

        try {
            const controller = new AbortController();
            abortRef.current = controller;

            const res = await fetch(`${API_BASE}/api/bidding/generate-full/${taskId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    company_data: companyData,
                    llm_provider: 'qwen',
                }),
                signal: controller.signal,
            });

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let gotComplete = false;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // SSE events are separated by double newlines
                const parts = buffer.split('\n\n');
                buffer = parts.pop() || ''; // keep incomplete last part

                for (const part of parts) {
                    for (const line of part.split('\n')) {
                        if (!line.startsWith('data: ')) continue;
                        try {
                            const data = JSON.parse(line.slice(6));
                            handleSSEEvent(data);
                            if (data.type === 'complete') gotComplete = true;
                        } catch (e) {
                            console.warn('SSE JSON parse error:', e.message, line.slice(0, 100));
                        }
                    }
                }
            }

            // Process any remaining data in buffer
            if (buffer.trim()) {
                for (const line of buffer.split('\n')) {
                    if (!line.startsWith('data: ')) continue;
                    try {
                        const data = JSON.parse(line.slice(6));
                        handleSSEEvent(data);
                        if (data.type === 'complete') gotComplete = true;
                    } catch (e) { /* ignore */ }
                }
            }

            // Fallback: if stream ended without 'complete', fetch results via REST
            if (!gotComplete && taskId) {
                console.warn('SSE stream ended without complete event, fetching via REST...');
                try {
                    const verifyRes = await fetch(`${API_BASE}/api/bidding/verify/${taskId}`, { method: 'POST' });
                    const verifyData = await verifyRes.json();
                    if (verifyData.success) {
                        setVerification(verifyData.data);
                    }
                    // Get task info for filename
                    const taskRes = await fetch(`${API_BASE}/api/bidding/tasks`);
                    const taskData = await taskRes.json();
                    const thisTask = taskData.data?.find(t => t.task_id === taskId);
                    if (thisTask?.has_output) {
                        setOutputFilename(`bid_document_${taskId}.docx`);
                    }
                    setStep(5);
                } catch (fallbackErr) {
                    console.error('Fallback fetch failed:', fallbackErr);
                    alert('生成可能已完成但未收到结果，请刷新页面后在任务列表中查看');
                }
            }
        } catch (err) {
            if (err.name === 'AbortError') return;
            alert('生成失败: ' + err.message);
        } finally {
            setGenerating(false);
            clearInterval(timerRef.current);
            abortRef.current = null;
        }
    };

    const handleSSEEvent = (data) => {
        switch (data.type) {
            case 'template_matched':
                setMatchedTemplate({ name: data.template_name, score: data.score, skeletons: data.skeleton_count });
                break;
            case 'start':
                setGenProgress(p => ({ ...p, total: data.total_sections, llmCount: data.llm_sections || 0, codeCount: data.code_sections || 0 }));
                break;
            case 'progress':
                setGenProgress(p => ({
                    ...p,
                    current: data.current,
                    sections: [...p.sections.filter(s => s.title !== data.section_title),
                    { title: data.section_title, status: 'generating', current: data.current, method: data.method || 'llm', type: data.section_type || '' }],
                }));
                break;
            case 'section_done':
                setGenProgress(p => ({
                    ...p,
                    current: data.current,
                    sections: p.sections.map(s =>
                        s.title === data.section_title
                            ? { ...s, status: data.status, length: data.content_length, missing: data.missing_fields }
                            : s
                    ),
                }));
                break;
            case 'section_error':
                setGenProgress(p => ({
                    ...p,
                    sections: p.sections.map(s =>
                        s.title === data.section_title ? { ...s, status: 'error', error: data.error } : s
                    ),
                }));
                break;
            case 'assembling':
            case 'verifying':
                setGenProgress(p => ({ ...p, phase: data.type, message: data.message }));
                break;
            case 'complete':
                setOutputFilename(data.filename || '');
                setVerification(data.verification);
                setStep(5);
                break;
            case 'error':
                alert(data.message);
                break;
        }
    };

    // ── Download .docx ──
    const handleDownload = async () => {
        if (!taskId) return;
        const a = document.createElement('a');
        a.href = `${API_BASE}/api/bidding/download/${taskId}`;
        a.download = outputFilename || 'bid_document.docx';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    };

    // ── Save as template ──
    const handleSaveTemplate = async () => {
        if (!taskId) return;
        try {
            const res = await fetch(`${API_BASE}/api/bidding/templates/save/${taskId}`, { method: 'POST' });
            const result = await res.json();
            if (result.success) {
                alert(`✅ 模板保存成功！ID: ${result.data.template_id}\n包含 ${result.data.sections} 个章节骨架`);
            } else {
                alert('保存失败: ' + result.message);
            }
        } catch (err) {
            alert('保存失败: ' + err.message);
        }
    };

    // ── Reset ──
    const reset = () => {
        setStep(1);
        setFile(null);
        setTaskId(null);
        setRequirements(null);
        setGenProgress({ current: 0, total: 0, sections: [], llmCount: 0, codeCount: 0 });
        setVerification(null);
        setOutputFilename('');
        setElapsed(0);
        setMatchedTemplate(null);
        if (abortRef.current) abortRef.current.abort();
        clearInterval(timerRef.current);
    };

    useEffect(() => () => { clearInterval(timerRef.current); if (abortRef.current) abortRef.current.abort(); }, []);

    // ── Step indicator ──
    const stepDefs = [
        { n: 1, label: '上传招标文件', icon: Upload },
        { n: 2, label: '确认投标结构', icon: ClipboardList },
        { n: 3, label: '逐章节生成', icon: Sparkles },
        { n: 4, label: '校验 & 下载', icon: Shield },
    ];

    const getStepState = (sn) => {
        const mapping = { 1: 1, 2: 1, 3: 2, 4: 3, 5: 4 };
        const currentLogical = mapping[step] || 1;
        if (sn === currentLogical) return 'active';
        if (sn < currentLogical) return 'done';
        return 'pending';
    };

    // ── Helper: count sections ──
    const totalSections = requirements?.volumes?.reduce((sum, v) => sum + (v.sections?.length || 0), 0) || 0;

    // ── Input field component ──
    const InputField = ({ icon: Icon, label, field, placeholder }) => (
        <div>
            <label className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest flex items-center mb-1">
                <Icon size={10} className="mr-1" />{label}
            </label>
            <input value={companyData[field]} onChange={e => updateCompany(field, e.target.value)}
                placeholder={placeholder}
                className="w-full bg-zinc-900 border border-zinc-700 rounded-sm px-3 py-1.5 text-[11px] text-zinc-300 focus:outline-none focus:border-orange-500 font-mono transition-colors" />
        </div>
    );

    return (
        <div className="p-6 max-w-5xl mx-auto">
            <style>{WORD_STYLES}</style>

            {/* Header */}
            <div className="flex items-center justify-between mb-5">
                <div>
                    <h2 className="text-lg font-bold text-zinc-900 flex items-center">
                        <FileText size={20} className="mr-2 text-orange-500" />
                        智能投标文件生成
                        <span className="ml-2 text-[9px] bg-orange-100 text-orange-600 px-1.5 py-0.5 rounded-sm font-mono">Phase 1</span>
                    </h2>
                    <p className="text-[11px] text-zinc-500 mt-0.5">上传招标文件 → 确认投标结构 → 逐章节 AI 生成 → 校验 & 下载 .docx</p>
                </div>
                <div className="flex items-center space-x-1">
                    {stepDefs.map((s, i) => {
                        const state = getStepState(s.n);
                        const Icon = s.icon;
                        return (
                            <div key={s.n} className="flex items-center">
                                <div className={`flex items-center text-[9px] font-bold uppercase tracking-widest px-2 py-1.5 rounded-full border transition-all ${state === 'active' ? 'bg-orange-500 text-white border-orange-500' :
                                    state === 'done' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                                        'bg-zinc-100 text-zinc-400 border-zinc-200'
                                    }`}>
                                    {state === 'done' ? <CheckCircle size={9} className="mr-1" /> : <Icon size={9} className="mr-1" />}
                                    {s.label}
                                </div>
                                {i < stepDefs.length - 1 && <ChevronRight size={12} className="text-zinc-300 mx-0.5" />}
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* ══════════ Step 1: 上传招标文件 ══════════ */}
            {step === 1 && (
                <div className="space-y-4 zoom-in">
                    <div className="bg-white border border-zinc-200 rounded-sm p-6 shadow-sm">
                        <div className="text-center">
                            <Upload size={40} className="mx-auto text-orange-400 mb-3" />
                            <h3 className="text-sm font-bold text-zinc-800 mb-1">上传招标文件</h3>
                            <p className="text-[11px] text-zinc-500 mb-4">
                                支持 .docx 格式，AI 将解析文档结构并提取投标要求（分册、章节、资质、格式）
                            </p>
                            <input ref={fileInputRef} type="file" accept=".docx" onChange={handleFileSelect} className="hidden" />
                            <div onClick={() => fileInputRef.current?.click()}
                                className="border-2 border-dashed border-zinc-300 rounded-sm p-8 cursor-pointer hover:border-orange-400 hover:bg-orange-50/50 transition-all group">
                                {file ? (
                                    <div className="flex items-center justify-center space-x-3">
                                        <FileText size={24} className="text-orange-500" />
                                        <div className="text-left">
                                            <div className="text-xs font-bold text-zinc-800">{file.name}</div>
                                            <div className="text-[10px] text-zinc-500">{(file.size / 1024).toFixed(1)} KB</div>
                                        </div>
                                    </div>
                                ) : (
                                    <p className="text-xs text-zinc-400 group-hover:text-orange-500 transition-colors">
                                        点击选择文件或拖拽到此处
                                    </p>
                                )}
                            </div>
                            {file && (
                                <button onClick={handleUploadAndParse}
                                    className="mt-4 bg-orange-500 text-white px-8 py-2.5 rounded-sm font-bold text-xs hover:bg-orange-600 transition-all shadow-lg flex items-center justify-center mx-auto space-x-2">
                                    <Sparkles size={14} /><span>开始 AI 解析</span>
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* ══════════ Step 2: AI 解析中 ══════════ */}
            {step === 2 && (
                <div className="bg-white border border-zinc-200 rounded-sm p-8 shadow-sm text-center zoom-in">
                    <Loader2 size={40} className="mx-auto text-orange-500 animate-spin mb-4" />
                    <h3 className="text-sm font-bold text-zinc-800 mb-1">正在解析招标文件结构...</h3>
                    <p className="text-[11px] text-zinc-500">python-docx 结构提取 + Qwen-Max 需求分析（约 1-3 分钟）</p>
                    <div className="mt-4 flex items-center justify-center space-x-6 text-[10px] text-zinc-400">
                        <span>📄 {file?.name}</span>
                        <span>📏 {file ? (file.size / 1024).toFixed(1) + ' KB' : ''}</span>
                        <span className="font-mono">{elapsed.toFixed(1)}s</span>
                        <span className="text-emerald-500 flex items-center">
                            <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full mr-1 animate-pulse"></span>Processing
                        </span>
                    </div>
                </div>
            )}

            {/* ══════════ Step 3: 确认投标结构 + 律所信息 ══════════ */}
            {step === 3 && requirements && (
                <div className="space-y-4 zoom-in">
                    {/* 解析结果概览 */}
                    <div className="bg-emerald-50 border border-emerald-200 rounded-sm p-4 shadow-sm">
                        <div className="flex items-center justify-between mb-3">
                            <div className="text-[10px] font-bold text-emerald-700 uppercase tracking-widest flex items-center">
                                <CheckCircle size={12} className="mr-1.5" />
                                招标文件结构解析完成 · {rawSectionsCount} 原始段落 · {requirements.volumes?.length || 0} 个分册 · {totalSections} 个章节
                            </div>
                            <span className="text-[10px] text-emerald-600 font-mono">{elapsed.toFixed(1)}s</span>
                        </div>

                        {/* 分册结构预览 */}
                        {requirements.volumes?.map((vol, vi) => (
                            <div key={vi} className="mb-3">
                                <div className="text-[10px] font-bold text-emerald-800 mb-1">{vol.name}</div>
                                <div className="grid grid-cols-2 gap-1">
                                    {vol.sections?.map((sec, si) => (
                                        <div key={si} className="bg-white border border-emerald-100 rounded-sm px-2 py-1 flex items-center text-[10px]">
                                            <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${sec.type === 'narrative' ? 'bg-blue-400' :
                                                sec.type === 'table' ? 'bg-purple-400' :
                                                    sec.type === 'form' ? 'bg-orange-400' :
                                                        'bg-amber-400'
                                                }`}></span>
                                            <span className="text-zinc-600 truncate">{sec.order}. {sec.title}</span>
                                            <span className="ml-auto text-zinc-400 text-[8px]">{sec.type}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}

                        {/* 格式/资质信息 */}
                        <div className="flex gap-3 mt-2">
                            {requirements.qualification_requirements?.length > 0 && (
                                <div className="flex-1">
                                    <div className="text-[9px] font-bold text-emerald-700 mb-1">资质要求</div>
                                    <div className="flex flex-wrap gap-1">
                                        {requirements.qualification_requirements.slice(0, 5).map((q, i) => (
                                            <span key={i} className="bg-white border border-emerald-200 text-emerald-700 text-[8px] px-1.5 py-0.5 rounded-full">{q}</span>
                                        ))}
                                    </div>
                                </div>
                            )}
                            {requirements.deadline_info?.submission_deadline && (
                                <div className="text-[9px]">
                                    <span className="text-emerald-600 font-bold">截止时间：</span>
                                    <span className="text-emerald-800">{requirements.deadline_info.submission_deadline}</span>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* 律所信息表单 */}
                    <div className="flex justify-between items-center">
                        <h3 className="text-xs font-bold text-zinc-700 uppercase tracking-widest">填写律所信息（可选，提高填充率）</h3>
                        <button onClick={fillDemo} className="text-[10px] text-orange-500 hover:text-orange-600 font-bold border border-orange-200 px-2 py-1 rounded-sm hover:bg-orange-50 transition-all">
                            🎯 填充 Demo 数据
                        </button>
                    </div>

                    <div className="bg-white border border-zinc-200 rounded-sm p-4 shadow-sm">
                        <div className="grid grid-cols-2 gap-3">
                            <InputField icon={Building2} label="律所名称" field="company_name" placeholder="湖南天衡律师事务所" />
                            <InputField icon={User} label="法定代表人" field="legal_rep" placeholder="张建明" />
                            <InputField icon={FileText} label="执业许可证号" field="license_no" placeholder="湘司律字第0088号" />
                            <InputField icon={MapPin} label="地址" field="address" placeholder="湖南省长沙市..." />
                            <InputField icon={Phone} label="联系电话" field="phone" placeholder="0731-88886666" />
                            <InputField icon={Mail} label="电子邮箱" field="email" placeholder="contact@firm.com" />
                            <InputField icon={Calendar} label="成立年份" field="established_year" placeholder="2003" />
                            <InputField icon={DollarSign} label="注册资本" field="registered_capital" placeholder="500万元" />
                        </div>
                    </div>

                    <button onClick={startGeneration}
                        className="w-full bg-orange-500 text-white py-3 rounded-sm font-bold text-sm hover:bg-orange-600 transition-all flex items-center justify-center space-x-2 shadow-lg hover:shadow-xl active:scale-[0.99]">
                        <Sparkles size={16} /><span>开始生成投标文件（{totalSections} 个章节）</span>
                    </button>
                </div>
            )}

            {/* ══════════ Step 4: 逐章节生成进度 ══════════ */}
            {step === 4 && (
                <div className="space-y-3 zoom-in">
                    <div className="bg-white border border-zinc-200 rounded-sm p-4 shadow-sm">
                        <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center space-x-3">
                                <Loader2 size={16} className="text-orange-500 animate-spin" />
                                <div>
                                    <div className="text-xs font-bold text-zinc-800">
                                        {genProgress.phase === 'assembling' ? '正在组装 Word 文档...' :
                                            genProgress.phase === 'verifying' ? '正在校验投标文件...' :
                                                `正在生成章节 ${genProgress.current}/${genProgress.total}`}
                                    </div>
                                    <div className="text-[10px] text-zinc-500">
                                        {genProgress.message || `代码模板 ${genProgress.codeCount} 个 · LLM 生成 ${genProgress.llmCount} 个`}
                                    </div>
                                </div>
                            </div>
                            <div className="text-[10px] text-zinc-400 font-mono">{elapsed.toFixed(1)}s</div>
                        </div>

                        {/* Progress bar */}
                        <div className="w-full bg-zinc-100 rounded-full h-1.5 mb-3">
                            <div className="bg-orange-500 h-1.5 rounded-full transition-all duration-500"
                                style={{ width: `${genProgress.total > 0 ? (genProgress.current / genProgress.total) * 100 : 0}%` }}></div>
                        </div>

                        {/* Section list */}
                        <div className="grid grid-cols-2 gap-1.5 max-h-80 overflow-y-auto">
                            {genProgress.sections.map((sec, i) => (
                                <div key={i} className={`flex items-center text-[10px] px-2 py-1.5 rounded-sm border ${sec.status === 'generating' ? 'bg-orange-50 border-orange-200 text-orange-700' :
                                    sec.status === 'error' ? 'bg-red-50 border-red-200 text-red-600' :
                                        sec.status === 'placeholder' ? 'bg-amber-50 border-amber-200 text-amber-700' :
                                            'bg-emerald-50 border-emerald-200 text-emerald-700'
                                    }`}>
                                    {sec.status === 'generating' ? <Loader2 size={10} className="mr-1.5 animate-spin" /> :
                                        sec.status === 'error' ? <XCircle size={10} className="mr-1.5" /> :
                                            sec.status === 'placeholder' ? <AlertTriangle size={10} className="mr-1.5" /> :
                                                <CheckCircle size={10} className="mr-1.5" />}
                                    <span className="truncate">{sec.title}</span>
                                    {sec.method && <span className={`ml-auto text-[7px] px-1 py-0.5 rounded font-bold ${sec.method === 'llm' ? 'bg-purple-100 text-purple-600' : 'bg-blue-100 text-blue-600'}`}>{sec.method === 'llm' ? 'LLM' : '模板'}</span>}
                                    {sec.length > 0 && <span className="ml-1 text-[8px] opacity-60">{sec.length}字</span>}
                                    {sec.missing?.length > 0 && <span className="ml-1 text-[8px] text-amber-600">({sec.missing.length}待补)</span>}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* ══════════ Step 5: 校验报告 + 下载 ══════════ */}
            {step === 5 && verification && (
                <div className="space-y-4 zoom-in">
                    {/* 整体状态 */}
                    <div className={`border rounded-sm p-4 shadow-sm ${verification.overall_status === 'PASS' ? 'bg-emerald-50 border-emerald-200' :
                        verification.overall_status === 'WARNING' ? 'bg-amber-50 border-amber-200' :
                            'bg-red-50 border-red-200'
                        }`}>
                        <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-3">
                                {verification.overall_status === 'PASS' ? <CheckCircle size={24} className="text-emerald-500" /> :
                                    verification.overall_status === 'WARNING' ? <AlertTriangle size={24} className="text-amber-500" /> :
                                        <XCircle size={24} className="text-red-500" />}
                                <div>
                                    <div className="text-sm font-bold text-zinc-800">
                                        投标文件生成完成 · 校验{verification.overall_status === 'PASS' ? '通过' : '有问题需关注'}
                                    </div>
                                    <div className="text-[10px] text-zinc-500 mt-0.5">
                                        {genProgress.sections.length} 个章节 · 耗时 {elapsed.toFixed(1)}s
                                    </div>
                                </div>
                            </div>
                            <div className="text-right">
                                <div className={`text-2xl font-bold font-mono ${verification.overall_score >= 80 ? 'text-emerald-600' :
                                    verification.overall_score >= 50 ? 'text-amber-600' :
                                        'text-red-600'
                                    }`}>{verification.overall_score}</div>
                                <div className="text-[9px] text-zinc-400">校验分数</div>
                            </div>
                        </div>

                        {/* Summary badges */}
                        <div className="flex space-x-3 mt-3">
                            <span className="text-[10px] bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-bold">
                                ✅ {verification.summary?.pass || 0} 通过
                            </span>
                            <span className="text-[10px] bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-bold">
                                ⚠️ {verification.summary?.warning || 0} 警告
                            </span>
                            <span className="text-[10px] bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-bold">
                                ❌ {verification.summary?.error || 0} 错误
                            </span>
                        </div>
                    </div>

                    {/* 缺项清单 */}
                    {verification.missing_items?.length > 0 && (
                        <div className="bg-white border border-zinc-200 rounded-sm p-4 shadow-sm">
                            <div className="text-[10px] font-bold text-amber-700 uppercase tracking-widest mb-2 flex items-center">
                                <AlertTriangle size={10} className="mr-1" />
                                待补充内容 ({verification.missing_items.length} 项)
                            </div>
                            <div className="grid grid-cols-2 gap-1.5 max-h-40 overflow-y-auto">
                                {verification.missing_items.slice(0, 20).map((item, i) => (
                                    <div key={i} className="flex items-center text-[10px] bg-amber-50 border border-amber-100 px-2 py-1 rounded-sm">
                                        <span className={`w-1 h-1 rounded-full mr-1.5 ${item.priority === 'HIGH' ? 'bg-red-500' : 'bg-amber-400'}`}></span>
                                        <span className="text-zinc-500 truncate">{item.section}：</span>
                                        <span className="text-amber-700 font-bold truncate">{item.field}</span>
                                    </div>
                                ))}
                                {verification.missing_items.length > 20 && (
                                    <div className="text-[9px] text-zinc-400 col-span-2">...还有 {verification.missing_items.length - 20} 项</div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* 合规警告 */}
                    {verification.compliance_warnings?.length > 0 && (
                        <div className="bg-white border border-zinc-200 rounded-sm p-4 shadow-sm">
                            <div className="text-[10px] font-bold text-orange-700 uppercase tracking-widest mb-2 flex items-center">
                                <Shield size={10} className="mr-1" />
                                合规用语警告 ({verification.compliance_warnings.length} 项)
                            </div>
                            <div className="space-y-1 max-h-32 overflow-y-auto">
                                {verification.compliance_warnings.map((w, i) => (
                                    <div key={i} className="text-[10px] text-zinc-600 flex items-start">
                                        <span className="text-orange-400 mr-1.5 mt-0.5">•</span>
                                        <span><b className="text-zinc-800">{w.target}</b>: {w.message}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 操作按钮 */}
                    <div className="flex space-x-3">
                        <button onClick={reset}
                            className="flex-1 border border-zinc-300 text-zinc-600 py-2.5 rounded-sm font-bold text-xs hover:bg-zinc-50 transition-all flex items-center justify-center space-x-2">
                            <RotateCcw size={14} /><span>重新开始</span>
                        </button>
                        <button onClick={handleSaveTemplate}
                            className="flex-1 border border-orange-300 text-orange-600 py-2.5 rounded-sm font-bold text-xs hover:bg-orange-50 transition-all flex items-center justify-center space-x-2">
                            <Copy size={14} /><span>存为模板</span>
                        </button>
                        <button onClick={handleDownload}
                            className="flex-[2] bg-blue-600 text-white py-2.5 rounded-sm font-bold text-xs hover:bg-blue-700 transition-all flex items-center justify-center space-x-2 shadow-lg">
                            <FileDown size={14} /><span>下载投标文件 (.docx)</span>
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
