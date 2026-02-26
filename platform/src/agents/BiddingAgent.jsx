import { useState, useRef, useEffect } from 'react';
import { FileText, Send, Loader2, CheckCircle, Building2, User, Phone, Mail, DollarSign, Calendar, MapPin, ClipboardList, Download, RotateCcw, Upload, Sparkles, AlertTriangle, ChevronRight, Eye } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

export default function BiddingAgent() {
    const [step, setStep] = useState(1); // 1=上传 2=AI解析中 3=填写信息 4=AI生成中 5=完成
    const [file, setFile] = useState(null);
    const [parsing, setParsing] = useState(false);
    const [parseResult, setParsResult] = useState(null);
    const [form, setForm] = useState({
        company_name: '', legal_representative: '', project_name: '', client_name: '',
        project_id: '', registered_capital: '', established_date: '', address: '',
        contact_person: '', contact_phone: '', contact_email: '', bid_amount: '',
        guarantee_amount: '', delegate_name: '', validity_days: '120',
        parsed_requirements: '', parsed_risks: '', budget: '',
    });
    const [output, setOutput] = useState('');
    const [generating, setGenerating] = useState(false);
    const [elapsed, setElapsed] = useState(0);
    const scrollRef = useRef(null);
    const abortRef = useRef(null);
    const timerRef = useRef(null);
    const fileInputRef = useRef(null);

    const update = (k, v) => setForm(prev => ({ ...prev, [k]: v }));

    // ── Demo 数据 ──
    const fillDemo = () => {
        setForm(prev => ({
            ...prev,
            company_name: '湖南天衡律师事务所',
            legal_representative: '张建明',
            registered_capital: '500万元',
            established_date: '2003年6月15日',
            address: '湖南省长沙市岳麓区潇湘中路328号',
            contact_person: '李敏',
            contact_phone: '0731-88886666',
            contact_email: 'limin@tianheng-law.com',
            bid_amount: '180万元（未含税）',
            delegate_name: '王涛',
        }));
    };

    // ── Step 1: 上传招标文件 ──
    const handleFileSelect = (e) => {
        const f = e.target.files[0];
        if (f) setFile(f);
    };

    const handleUploadAndParse = async () => {
        if (!file) return;
        setStep(2);
        setParsing(true);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const res = await fetch(`${API_BASE}/api/bidding/parse`, {
                method: 'POST',
                body: formData,
            });

            const result = await res.json();

            if (result.success && result.data?.parsed) {
                const p = result.data.parsed;
                setParsResult(result.data);

                // 自动填充解析出的字段到表单
                setForm(prev => ({
                    ...prev,
                    project_name: p.project_name || prev.project_name,
                    client_name: p.client_name || prev.client_name,
                    project_id: p.project_id || prev.project_id,
                    guarantee_amount: p.guarantee_amount || prev.guarantee_amount,
                    validity_days: p.validity_days ? String(p.validity_days).replace(/[^\d]/g, '') || '120' : prev.validity_days,
                    budget: p.budget || prev.budget,
                    parsed_requirements: Array.isArray(p.requirements) ? p.requirements.join('\n') : (p.requirements || ''),
                    parsed_risks: Array.isArray(p.disqualification_risks) ? p.disqualification_risks.join('\n') : (p.disqualification_risks || ''),
                }));
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
        }
    };

    // ── 跳过上传，手动填写 ──
    const skipUpload = () => setStep(3);

    // ── Step 4: 生成标书 ──
    const generate = async () => {
        if (!form.company_name || !form.legal_representative || !form.project_name || !form.client_name) return;
        setStep(4);
        setOutput('');
        setGenerating(true);
        setElapsed(0);
        timerRef.current = setInterval(() => setElapsed(p => p + 0.1), 100);

        try {
            const controller = new AbortController();
            abortRef.current = controller;
            const res = await fetch(`${API_BASE}/api/bidding/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ...form, stream: true }),
                signal: controller.signal,
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let full = '';
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const text = decoder.decode(value, { stream: true });
                for (const line of text.split('\n')) {
                    if (!line.startsWith('data: ')) continue;
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.done) break;
                        full += data.content;
                        setOutput(full);
                    } catch (e) { /* partial */ }
                }
            }
            setOutput(full || '[无响应]');
            setStep(5);
        } catch (err) {
            if (err.name === 'AbortError') return;
            setOutput(`[连接错误] ${err.message}\n\n请确认后端服务运行在 localhost:8000`);
            setStep(5);
        } finally {
            setGenerating(false);
            clearInterval(timerRef.current);
            abortRef.current = null;
        }
    };

    const reset = () => {
        setStep(1); setOutput(''); setElapsed(0); setFile(null); setParsResult(null);
        setForm({
            company_name: '', legal_representative: '', project_name: '', client_name: '',
            project_id: '', registered_capital: '', established_date: '', address: '',
            contact_person: '', contact_phone: '', contact_email: '', bid_amount: '',
            guarantee_amount: '', delegate_name: '', validity_days: '120',
            parsed_requirements: '', parsed_risks: '', budget: ''
        });
        if (abortRef.current) abortRef.current.abort();
        clearInterval(timerRef.current);
    };

    useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [output]);
    useEffect(() => () => { clearInterval(timerRef.current); if (abortRef.current) abortRef.current.abort(); }, []);

    // ── 步骤指示器 ──
    const steps = [
        { n: 1, label: '上传招标文件', covers: [1, 2] },
        { n: 2, label: 'AI 智能解析', covers: [2] },
        { n: 3, label: '填写投标信息', covers: [3] },
        { n: 4, label: 'AI 生成标书', covers: [4, 5] },
    ];

    const getStepState = (s) => {
        if (step === 2 && s.n === 2) return 'active';
        if (step === 4 && s.n === 4) return 'active';
        if (s.covers.includes(step)) return 'active';
        const maxCover = Math.max(...s.covers);
        if (step > maxCover) return 'done';
        return 'pending';
    };

    const InputField = ({ icon: Icon, label, field, placeholder, required, wide }) => (
        <div className={wide ? 'col-span-2' : ''}>
            <label className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest flex items-center mb-1">
                <Icon size={10} className="mr-1" />{label}{required && <span className="text-red-500 ml-0.5">*</span>}
            </label>
            <input value={form[field]} onChange={e => update(field, e.target.value)}
                placeholder={placeholder}
                className="w-full bg-zinc-900 border border-zinc-700 rounded-sm px-3 py-1.5 text-[11px] text-zinc-300 focus:outline-none focus:border-orange-500 font-mono transition-colors" />
        </div>
    );

    return (
        <div className="p-6 max-w-5xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-5">
                <div>
                    <h2 className="text-lg font-bold text-zinc-900 flex items-center">
                        <FileText size={20} className="mr-2 text-orange-500" />
                        智能投标文件生成
                    </h2>
                    <p className="text-[11px] text-zinc-500 mt-0.5">上传招标文件 → AI 解析要求 → 填写投标信息 → 自动生成标书框架</p>
                </div>
                <div className="flex items-center space-x-1">
                    {steps.map((s, i) => {
                        const state = getStepState(s);
                        return (
                            <div key={s.n} className="flex items-center">
                                <div className={`flex items-center text-[9px] font-bold uppercase tracking-widest px-2.5 py-1.5 rounded-full border transition-all ${state === 'active' ? 'bg-orange-500 text-white border-orange-500' :
                                        state === 'done' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                                            'bg-zinc-100 text-zinc-400 border-zinc-200'
                                    }`}>
                                    {state === 'done' ? <CheckCircle size={9} className="mr-1" /> : null}
                                    {s.label}
                                </div>
                                {i < steps.length - 1 && <ChevronRight size={12} className="text-zinc-300 mx-0.5" />}
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
                            <p className="text-[11px] text-zinc-500 mb-4">支持 .docx / .txt 格式，AI 将自动解析项目名称、预算、资质要求等关键信息</p>

                            <input ref={fileInputRef} type="file" accept=".docx,.txt" onChange={handleFileSelect} className="hidden" />

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
                                    <div>
                                        <p className="text-xs text-zinc-400 group-hover:text-orange-500 transition-colors">点击选择文件或拖拽到此处</p>
                                    </div>
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

                    <div className="text-center">
                        <button onClick={skipUpload} className="text-[10px] text-zinc-400 hover:text-orange-500 transition-colors underline">
                            跳过上传，直接填写投标信息 →
                        </button>
                    </div>
                </div>
            )}

            {/* ══════════ Step 2: AI 解析中 ══════════ */}
            {step === 2 && (
                <div className="bg-white border border-zinc-200 rounded-sm p-8 shadow-sm text-center zoom-in">
                    <Loader2 size={40} className="mx-auto text-orange-500 animate-spin mb-4" />
                    <h3 className="text-sm font-bold text-zinc-800 mb-1">Qwen-Max 正在解析招标文件...</h3>
                    <p className="text-[11px] text-zinc-500">正在提取项目名称、预算金额、资质要求、否决条件等关键信息</p>
                    <div className="mt-4 flex items-center justify-center space-x-6 text-[10px] text-zinc-400">
                        <span>📄 {file?.name}</span>
                        <span>📏 {file ? (file.size / 1024).toFixed(1) + ' KB' : ''}</span>
                        <span className="text-emerald-500 flex items-center"><span className="w-1.5 h-1.5 bg-emerald-500 rounded-full mr-1 animate-pulse"></span>Processing</span>
                    </div>
                </div>
            )}

            {/* ══════════ Step 3: 填写投标信息（含解析结果） ══════════ */}
            {step === 3 && (
                <div className="space-y-4 zoom-in">
                    {/* 解析结果摘要 */}
                    {parseResult && (
                        <div className="bg-emerald-50 border border-emerald-200 rounded-sm p-4 shadow-sm">
                            <div className="flex items-center justify-between mb-2">
                                <div className="text-[10px] font-bold text-emerald-700 uppercase tracking-widest flex items-center">
                                    <CheckCircle size={12} className="mr-1.5" />
                                    招标文件解析完成 · {parseResult.filename} · {parseResult.text_length} 字 · {parseResult.model}
                                </div>
                            </div>
                            {parseResult.parsed && (
                                <div className="grid grid-cols-3 gap-2 text-[10px]">
                                    {parseResult.parsed.budget && parseResult.parsed.budget !== '未明确' && (
                                        <div className="bg-white rounded-sm px-2 py-1.5 border border-emerald-100">
                                            <span className="text-zinc-500">预算：</span>
                                            <span className="text-emerald-700 font-bold">{parseResult.parsed.budget}</span>
                                        </div>
                                    )}
                                    {parseResult.parsed.evaluation_method && parseResult.parsed.evaluation_method !== '未明确' && (
                                        <div className="bg-white rounded-sm px-2 py-1.5 border border-emerald-100">
                                            <span className="text-zinc-500">评标：</span>
                                            <span className="text-emerald-700 font-bold">{parseResult.parsed.evaluation_method}</span>
                                        </div>
                                    )}
                                    {parseResult.parsed.bid_method && parseResult.parsed.bid_method !== '未明确' && (
                                        <div className="bg-white rounded-sm px-2 py-1.5 border border-emerald-100">
                                            <span className="text-zinc-500">方式：</span>
                                            <span className="text-emerald-700 font-bold">{parseResult.parsed.bid_method}</span>
                                        </div>
                                    )}
                                </div>
                            )}
                            {parseResult.parsed?.requirements?.length > 0 && (
                                <div className="mt-2">
                                    <div className="text-[9px] text-emerald-600 font-bold mb-1">关键要求：</div>
                                    <div className="flex flex-wrap gap-1">
                                        {parseResult.parsed.requirements.map((r, i) => (
                                            <span key={i} className="bg-white border border-emerald-200 text-emerald-700 text-[9px] px-2 py-0.5 rounded-full">{r}</span>
                                        ))}
                                    </div>
                                </div>
                            )}
                            {parseResult.parsed?.disqualification_risks?.length > 0 && (
                                <div className="mt-2">
                                    <div className="text-[9px] text-red-600 font-bold mb-1 flex items-center">
                                        <AlertTriangle size={9} className="mr-1" />否决风险：
                                    </div>
                                    <div className="flex flex-wrap gap-1">
                                        {parseResult.parsed.disqualification_risks.map((r, i) => (
                                            <span key={i} className="bg-red-50 border border-red-200 text-red-600 text-[9px] px-2 py-0.5 rounded-full">{r}</span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    <div className="flex justify-between items-center">
                        <h3 className="text-xs font-bold text-zinc-700 uppercase tracking-widest">
                            {parseResult ? '确认并补充投标信息' : '投标基本信息'}
                        </h3>
                        <button onClick={fillDemo} className="text-[10px] text-orange-500 hover:text-orange-600 font-bold border border-orange-200 px-2 py-1 rounded-sm hover:bg-orange-50 transition-all">
                            🎯 填充 Demo 数据
                        </button>
                    </div>

                    {/* 自动填充的招标方信息 */}
                    <div className="bg-white border border-zinc-200 rounded-sm p-4 shadow-sm">
                        <div className="text-[9px] text-orange-600 font-bold uppercase tracking-widest mb-3 flex items-center">
                            <span className="w-1.5 h-1.5 bg-orange-500 rounded-full mr-1.5"></span>
                            {parseResult ? '以下字段已从招标文件自动提取（可修改）' : '核心信息（必填）'}
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <InputField icon={ClipboardList} label="项目名称" field="project_name" placeholder="从招标文件提取或手动输入" required />
                            <InputField icon={Building2} label="招标人名称" field="client_name" placeholder="从招标文件提取或手动输入" required />
                            <InputField icon={FileText} label="项目编号" field="project_id" placeholder="HNYD-2026-FW-0032" />
                            <InputField icon={DollarSign} label="预算/最高限价" field="budget" placeholder="195万元" />
                            <InputField icon={DollarSign} label="保证金金额" field="guarantee_amount" placeholder="3.6万元" />
                            <InputField icon={Calendar} label="有效期(天)" field="validity_days" placeholder="120" />
                        </div>
                    </div>

                    {/* 投标人信息 */}
                    <div className="bg-white border border-zinc-200 rounded-sm p-4 shadow-sm">
                        <div className="text-[9px] text-blue-600 font-bold uppercase tracking-widest mb-3 flex items-center">
                            <span className="w-1.5 h-1.5 bg-blue-500 rounded-full mr-1.5"></span>投标人信息（必填 *）
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <InputField icon={Building2} label="投标人名称" field="company_name" placeholder="湖南天衡律师事务所" required />
                            <InputField icon={User} label="法定代表人" field="legal_representative" placeholder="张建明" required />
                            <InputField icon={DollarSign} label="注册资本" field="registered_capital" placeholder="500万元" />
                            <InputField icon={Calendar} label="成立时间" field="established_date" placeholder="2003年6月15日" />
                            <InputField icon={MapPin} label="注册地址" field="address" placeholder="湖南省长沙市..." />
                            <InputField icon={User} label="联系人" field="contact_person" placeholder="李敏" />
                            <InputField icon={Phone} label="联系电话" field="contact_phone" placeholder="0731-88886666" />
                            <InputField icon={Mail} label="电子邮箱" field="contact_email" placeholder="contact@firm.com" />
                            <InputField icon={DollarSign} label="投标报价" field="bid_amount" placeholder="180万元" />
                            <InputField icon={User} label="委托代理人" field="delegate_name" placeholder="无则留空" />
                        </div>
                    </div>

                    <button onClick={generate}
                        disabled={!form.company_name || !form.legal_representative || !form.project_name || !form.client_name}
                        className="w-full bg-orange-500 text-white py-3 rounded-sm font-bold text-sm hover:bg-orange-600 transition-all disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center space-x-2 shadow-lg hover:shadow-xl active:scale-[0.99]">
                        <Send size={16} /><span>开始生成投标文件框架</span>
                    </button>
                </div>
            )}

            {/* ══════════ Step 4 & 5: 生成中 / 完成 ══════════ */}
            {(step === 4 || step === 5) && (
                <div className="space-y-3 zoom-in">
                    <div className="flex items-center justify-between bg-white border border-zinc-200 rounded-sm p-3 shadow-sm">
                        <div className="flex items-center space-x-3">
                            {generating ? <Loader2 size={16} className="text-orange-500 animate-spin" /> : <CheckCircle size={16} className="text-emerald-500" />}
                            <div>
                                <div className="text-xs font-bold text-zinc-800">
                                    {generating ? 'Qwen-Max 正在生成投标文件框架...' : '投标文件框架生成完成'}
                                </div>
                                <div className="text-[10px] text-zinc-500 mt-0.5">{form.company_name} → {form.project_name}</div>
                            </div>
                        </div>
                        <div className="flex items-center space-x-3 text-[10px]">
                            <span className="text-zinc-400 font-mono">{elapsed.toFixed(1)}s</span>
                            <span className="text-zinc-400 font-mono">{output.length} 字</span>
                            {generating && <span className="text-emerald-500 font-bold flex items-center"><span className="w-1.5 h-1.5 bg-emerald-500 rounded-full mr-1 animate-pulse"></span>Streaming</span>}
                        </div>
                    </div>

                    <div ref={scrollRef}
                        className="bg-white border border-zinc-200 rounded-sm p-5 shadow-sm overflow-y-auto font-mono text-[11px] text-zinc-700 leading-relaxed whitespace-pre-wrap"
                        style={{ maxHeight: 'calc(100vh - 320px)', minHeight: '400px' }}>
                        {output}
                        {generating && <span className="inline-block w-1.5 h-4 bg-orange-500 ml-0.5 animate-pulse"></span>}
                    </div>

                    {step === 5 && (
                        <div className="flex space-x-3">
                            <button onClick={reset}
                                className="flex-1 border border-zinc-300 text-zinc-600 py-2.5 rounded-sm font-bold text-xs hover:bg-zinc-50 transition-all flex items-center justify-center space-x-2">
                                <RotateCcw size={14} /><span>重新开始</span>
                            </button>
                            <button onClick={() => { navigator.clipboard.writeText(output); }}
                                className="flex-1 bg-orange-500 text-white py-2.5 rounded-sm font-bold text-xs hover:bg-orange-600 transition-all flex items-center justify-center space-x-2 shadow-lg">
                                <Download size={14} /><span>复制全文</span>
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
