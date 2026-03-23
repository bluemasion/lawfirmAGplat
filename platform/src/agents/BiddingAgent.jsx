import { useState, useRef, useEffect } from 'react';
import { FileText, Loader2, CheckCircle, Download, Upload, Sparkles, RotateCcw, Send, AlertTriangle, ChevronDown, Eye, X, Package } from 'lucide-react';
import MaterialPanel from './MaterialPanel';

const API_BASE = 'http://localhost:8000';

export default function BiddingAgent() {
    const [messages, setMessages] = useState([
        { role: 'ai', content: '👋 欢迎使用智能投标文件生成系统。请上传招标文件 (.docx)，我将解析结构并生成完整投标文件。', type: 'text', time: new Date() },
    ]);
    const [taskId, setTaskId] = useState(null);
    const [requirements, setRequirements] = useState(null);
    const [outputFilename, setOutputFilename] = useState('');
    const [processing, setProcessing] = useState(false);  // true when AI is working
    const [phase, setPhase] = useState('idle'); // idle | parsing | ready | generating | done
    const [showStructure, setShowStructure] = useState(false);
    const [showMaterialPanel, setShowMaterialPanel] = useState(false);

    // Company data for generation
    const [companyData, setCompanyData] = useState({
        company_name: '', legal_rep: '', license_no: '', address: '',
        phone: '', email: '', established_year: '', lawyer_count: '',
        partner_count: '', registered_capital: '',
    });

    const fileInputRef = useRef(null);
    const materialInputRef = useRef(null);
    const chatEndRef = useRef(null);
    const abortRef = useRef(null);

    // Auto-scroll to bottom when messages change
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // ── Helpers ──
    const addMsg = (role, content, type = 'text') => {
        setMessages(prev => [...prev, { role, content, type, time: new Date() }]);
    };

    const updateLastAiMsg = (content) => {
        setMessages(prev => {
            const updated = [...prev];
            for (let i = updated.length - 1; i >= 0; i--) {
                if (updated[i].role === 'ai' && updated[i].type === 'stream') {
                    updated[i] = { ...updated[i], content: updated[i].content + '\n' + content };
                    return updated;
                }
            }
            return [...prev, { role: 'ai', content, type: 'stream', time: new Date() }];
        });
    };

    // ── Fill demo data ──
    const fillDemo = () => {
        const demo = {
            company_name: '北京市天元律师事务所', legal_rep: '朱小辉',
            license_no: '司发证字〔1993〕177号', address: '北京市朝阳区东三环中路1号环球金融中心',
            phone: '010-65150088', email: 'info@tylaw.com.cn',
            established_year: '1993', lawyer_count: '600',
            partner_count: '170', registered_capital: '',
        };
        setCompanyData(demo);
        addMsg('user', '🎯 填充天元律所数据');
        addMsg('ai', `✅ 已填充天元律师事务所信息:\n• 律所: ${demo.company_name}\n• 代表人: ${demo.legal_rep}\n• 律师: ${demo.lawyer_count}人\n• 成立: ${demo.established_year}年`);
    };

    // ── Upload tender file → SSE parse ──
    const handleTenderUpload = async (file) => {
        if (!file || !file.name.endsWith('.docx')) {
            addMsg('ai', '⚠️ 请上传 .docx 格式的招标文件。');
            return;
        }

        addMsg('user', `📄 上传招标文件: ${file.name} (${(file.size / 1024).toFixed(1)}KB)`);
        setProcessing(true);
        setPhase('parsing');

        // Start streaming AI log
        setMessages(prev => [...prev, { role: 'ai', content: '', type: 'stream', time: new Date() }]);

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('llm_provider', 'qwen');

            const res = await fetch(`${API_BASE}/api/bidding/parse-structure`, {
                method: 'POST', body: formData,
            });

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    try {
                        const ev = JSON.parse(line.slice(6));
                        if (ev.type === 'log') {
                            updateLastAiMsg(ev.message);
                        } else if (ev.type === 'phase') {
                            updateLastAiMsg(ev.message);
                        } else if (ev.type === 'section') {
                            updateLastAiMsg(`   ${ev.icon || '📄'} ${ev.title}  → ${ev.type}`);
                        } else if (ev.type === 'complete') {
                            setTaskId(ev.task_id);
                            setRequirements(ev.requirements);
                            setPhase('ready');

                            const vols = ev.requirements?.volumes || [];
                            const totalSecs = vols.reduce((s, v) => s + (v.sections?.length || 0), 0);
                            updateLastAiMsg(`\n✅ 解析完成! 共 ${totalSecs} 个章节`);
                            addMsg('ai', `招标文件解析完成，请查看文件结构并确认。`, 'action');
                        } else if (ev.type === 'error') {
                            updateLastAiMsg('❌ 错误: ' + ev.message);
                            setPhase('idle');
                        }
                    } catch { }
                }
            }
        } catch (err) {
            addMsg('ai', '❌ 上传失败: ' + err.message);
            setPhase('idle');
        } finally {
            setProcessing(false);
        }
    };

    // ── Upload material files ──
    const handleMaterialUpload = async (files) => {
        if (!files.length) return;
        const names = Array.from(files).map(f => f.name).join(', ');
        addMsg('user', `📎 上传素材: ${names}`);
        setProcessing(true);

        try {
            for (const mf of files) {
                const formData = new FormData();
                formData.append('file', mf);
                formData.append('llm_provider', 'qwen');

                addMsg('ai', `🔍 正在解析 ${mf.name}...`, 'text');

                const res = await fetch(`${API_BASE}/api/bidding/upload-historical`, {
                    method: 'POST', body: formData,
                });
                const result = await res.json();

                if (!result.success) {
                    addMsg('ai', `❌ 解析失败: ${result.message}`);
                    continue;
                }

                const { upload_id, extracted, diff, materials } = result.data;

                // Build diff display message
                let diffMsg = `📋 **${mf.name}** 提取完成:\n`;

                // Resumes
                if (diff.resumes?.length) {
                    diffMsg += `\n**👤 律师简历 (${diff.resumes.length}人)**\n`;
                    for (const r of diff.resumes) {
                        const name = r.name || r.data?.name || '未知';
                        const spec = r.data?.specialty || '';
                        if (r.action === 'new') {
                            diffMsg += `  🆕 ${name}${spec ? ' — ' + spec : ''}\n`;
                        } else if (r.action === 'updated') {
                            diffMsg += `  🔄 ${name} (有更新)\n`;
                            for (const [field, [oldV, newV]] of Object.entries(r.changes || {})) {
                                diffMsg += `      ${field}: ${oldV || '无'} → ${newV}\n`;
                            }
                        } else {
                            diffMsg += `  ✅ ${name} (已存在，无变化)\n`;
                        }
                    }
                }

                // Projects
                if (diff.projects?.length) {
                    diffMsg += `\n**💼 项目业绩 (${diff.projects.length}个)**\n`;
                    for (const p of diff.projects) {
                        const name = p.project_name || p.data?.project_name || '未知项目';
                        if (p.action === 'new') diffMsg += `  🆕 ${name}\n`;
                        else if (p.action === 'updated') diffMsg += `  🔄 ${name} (有更新)\n`;
                        else diffMsg += `  ✅ ${name} (无变化)\n`;
                    }
                }

                // Qualifications
                if (diff.qualifications?.length) {
                    diffMsg += `\n**🏅 资质证书 (${diff.qualifications.length}项)**\n`;
                    for (const q of diff.qualifications) {
                        const name = q.name || q.data?.name || '未知';
                        if (q.action === 'new') diffMsg += `  🆕 ${name}\n`;
                        else if (q.action === 'updated') diffMsg += `  🔄 ${name} (有更新)\n`;
                        else diffMsg += `  ✅ ${name} (无变化)\n`;
                    }
                }

                // Narrative chunks
                if (diff.narrative_chunks?.length) {
                    diffMsg += `\n**📄 参考范文 ${diff.narrative_chunks.length} 段**\n`;
                }

                if (!diff.resumes?.length && !diff.projects?.length && !diff.qualifications?.length && !diff.narrative_chunks?.length) {
                    diffMsg += '\n⚠️ 未能从文件中提取到任何数据';
                }

                addMsg('ai', diffMsg.trim());

                // Add action button for confirmation (any extracted data)
                if (diff.resumes?.length || diff.projects?.length || diff.qualifications?.length || diff.narrative_chunks?.length) {
                    setMessages(prev => [...prev, {
                        role: 'ai', type: 'action',
                        content: '确认以上提取结果无误？',
                        actions: [
                            { label: '✅ 确认入库', action: 'confirm_materials', uploadId: upload_id },
                            { label: '⏭️ 跳过', action: 'skip_materials' },
                        ],
                        time: new Date(),
                    }]);
                }
            }
        } catch (err) {
            addMsg('ai', '❌ 素材上传失败: ' + err.message);
        } finally {
            setProcessing(false);
        }
    };

    // ── Confirm materials after user review ──
    const confirmMaterials = async (uploadId) => {
        setProcessing(true);
        try {
            const res = await fetch(`${API_BASE}/api/bidding/confirm-materials`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ upload_id: uploadId }),
            });
            const result = await res.json();
            if (result.success) {
                const saved = result.data.saved;
                const total = result.data.total_store;
                let msg = '✅ 素材已入库！';
                if (saved.resumes) msg += `\n• 👤 ${saved.resumes} 位律师简历`;
                if (saved.projects) msg += `\n• 💼 ${saved.projects} 个项目业绩`;
                if (saved.qualifications) msg += `\n• 🏅 ${saved.qualifications} 项资质`;
                if (saved.narrative_chunks) msg += `\n• 📄 ${saved.narrative_chunks} 段范文`;
                msg += `\n\n📊 素材库总量: ${total.resumes}简历 / ${total.projects}项目 / ${total.qualifications}资质 / ${total.narrative_chunks}范文`;
                addMsg('ai', msg);
            } else {
                addMsg('ai', '❌ 入库失败: ' + result.message);
            }
        } catch (err) {
            addMsg('ai', '❌ 入库失败: ' + err.message);
        } finally {
            setProcessing(false);
        }
    };

    // ── Start generation → SSE stream ──
    const startGeneration = async () => {
        if (!taskId) {
            addMsg('ai', '⚠️ 请先上传招标文件并完成解析。');
            return;
        }

        const totalSections = requirements?.volumes?.reduce((s, v) => s + (v.sections?.length || 0), 0) || 0;
        addMsg('user', `▶️ 开始生成投标文件 (${totalSections} 章节)`);
        setProcessing(true);
        setPhase('generating');

        // Start streaming AI log
        setMessages(prev => [...prev, { role: 'ai', content: `🚀 开始生成 ${totalSections} 个章节...`, type: 'stream', time: new Date() }]);

        try {
            const res = await fetch(`${API_BASE}/api/bidding/generate-full/${taskId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ company_data: companyData, llm_provider: 'qwen' }),
            });

            if (!res.ok) throw new Error(`HTTP ${res.status}`);

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let doneCount = 0;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const ds = line.slice(6);
                    if (ds === '[DONE]') break;
                    try {
                        const ev = JSON.parse(ds);
                        if (ev.type === 'start') {
                            updateLastAiMsg(`📋 总计 ${ev.total_sections} 章节: ${ev.code_sections} 个模板填充 + ${ev.llm_sections} 个 AI 生成`);
                        } else if (ev.type === 'template_matched') {
                            updateLastAiMsg(`📎 匹配到模板: ${ev.template_name} (相似度 ${(ev.score * 100).toFixed(0)}%)`);
                        } else if (ev.type === 'progress') {
                            const method = ev.method === 'llm' ? '🤖 AI' : '⚡ 模板';
                            updateLastAiMsg(`[${ev.current}/${ev.total}] ${ev.section_title} → ${method} 生成中...`);
                        } else if (ev.type === 'section_done') {
                            doneCount++;
                            const icon = ev.status === 'generated' ? '✅' : ev.status === 'error' ? '❌' : '⚡';
                            updateLastAiMsg(`[${doneCount}/${totalSections}] ${ev.section_title} → ${icon} ${ev.content_length || 0}字`);
                        } else if (ev.type === 'section_error') {
                            doneCount++;
                            updateLastAiMsg(`[${doneCount}/${totalSections}] ${ev.section_title} → ❌ ${ev.error}`);
                        } else if (ev.type === 'assembling') {
                            updateLastAiMsg(`\n📦 ${ev.message}`);
                        } else if (ev.type === 'verifying') {
                            updateLastAiMsg(`🔍 ${ev.message}`);
                        } else if (ev.type === 'complete') {
                            setOutputFilename(ev.file_path);
                            setPhase('done');

                            let summary = '\n\n🎉 投标文件生成完成!';
                            if (ev.section_count) summary += `\n• ${ev.section_count} 个章节`;
                            if (ev.page_estimate) summary += `\n• 约 ${ev.page_estimate} 页`;
                            if (ev.verification) {
                                const v = ev.verification;
                                summary += `\n\n📊 校验报告:`;
                                summary += `\n• 总章节: ${v.total_sections || totalSections}`;
                                summary += `\n• 占位符率: ${v.placeholder_rate || 'N/A'}`;
                                if (v.company_mentions) summary += `\n• 律所名称: 出现 ${v.company_mentions} 次`;
                            }
                            summary += `\n\n📥 点击下方按钮下载文件`;
                            updateLastAiMsg(summary);
                        }
                    } catch { }
                }
            }
        } catch (err) {
            addMsg('ai', '❌ 生成失败: ' + err.message);
            setPhase('ready');
        } finally {
            setProcessing(false);
        }
    };

    // ── Download ──
    const handleDownload = () => {
        if (!outputFilename || !taskId) return;
        const url = `${API_BASE}/api/bidding/download/${taskId}`;
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', outputFilename.split('/').pop());
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        addMsg('user', '📥 下载投标文件');
        addMsg('ai', `✅ 已开始下载: ${outputFilename.split('/').pop()}`);
    };

    // ── Reset ──
    const reset = () => {
        setMessages([
            { role: 'ai', content: '👋 已重置。请上传新的招标文件 (.docx)。', type: 'text', time: new Date() },
        ]);
        setTaskId(null);
        setRequirements(null);
        setOutputFilename('');
        setProcessing(false);
        setPhase('idle');
        setCompanyData({
            company_name: '', legal_rep: '', license_no: '', address: '',
            phone: '', email: '', established_year: '', lawyer_count: '',
            partner_count: '', registered_capital: '',
        });
    };

    // ── Drag & drop on the whole chat area ──
    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        const file = e.dataTransfer.files[0];
        if (!file) return;
        if (phase === 'idle' || phase === 'ready') {
            if (file.name.endsWith('.docx')) {
                if (!taskId) {
                    handleTenderUpload(file);
                } else {
                    handleMaterialUpload([file]);
                }
            } else {
                addMsg('ai', '⚠️ 请上传 .docx 格式文件。');
            }
        }
    };

    // ── Render message content ──
    const renderContent = (msg) => {
        const lines = msg.content.split('\n').filter(l => l !== '');
        return lines.map((line, i) => {
            // Phase lines (orange)
            if (line.startsWith('🔍') || line.startsWith('🤖') || line.startsWith('🔗') || line.startsWith('🚀')) {
                return <div key={i} className="text-orange-400 font-semibold mt-1">{line}</div>;
            }
            // Success lines (green)
            if (line.startsWith('✅') || line.startsWith('🎉')) {
                return <div key={i} className="text-emerald-400 font-semibold mt-1">{line}</div>;
            }
            // Error lines (red)
            if (line.startsWith('❌') || line.startsWith('⚠️')) {
                return <div key={i} className="text-red-400 font-semibold">{line}</div>;
            }
            // Section lines (dimmed)
            if (line.trimStart().startsWith('📄') || line.trimStart().startsWith('📝') || line.trimStart().startsWith('📊') || line.trimStart().startsWith('📋') || line.trimStart().startsWith('🏅')) {
                return <div key={i} className="text-zinc-400 text-[11px] pl-2">{line}</div>;
            }
            // Progress lines [n/m]
            if (line.match(/^\[[\d]+\/[\d]+\]/)) {
                const isOk = line.includes('✅');
                const isErr = line.includes('❌');
                return <div key={i} className={`text-[11px] ${isErr ? 'text-red-400' : isOk ? 'text-zinc-400' : 'text-orange-300'}`}>{line}</div>;
            }
            // Bullet points
            if (line.trimStart().startsWith('•')) {
                return <div key={i} className="text-zinc-300 text-[11px] pl-2">{line}</div>;
            }
            // Default
            return <div key={i} className="text-zinc-200">{line}</div>;
        });
    };

    return (
        <>
            <div className="h-full flex flex-col bg-zinc-950"
                onDragOver={(e) => { e.preventDefault(); }}
                onDrop={handleDrop}>

                {/* ── Header ── */}
                <div className="flex items-center justify-between px-4 py-2.5 border-b border-zinc-800 bg-zinc-900/80 backdrop-blur shrink-0">
                    <div className="flex items-center space-x-2">
                        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-orange-500 to-amber-600 flex items-center justify-center shadow-lg shadow-orange-500/20">
                            <FileText size={14} className="text-white" />
                        </div>
                        <div>
                            <h1 className="text-[13px] font-bold text-zinc-100">智能投标文件生成</h1>
                            <p className="text-[9px] text-zinc-500 uppercase tracking-widest">
                                {phase === 'idle' && '等待上传'}
                                {phase === 'parsing' && '解析中...'}
                                {phase === 'ready' && `就绪 · ${requirements?.volumes?.reduce((s, v) => s + (v.sections?.length || 0), 0) || 0} 章节`}
                                {phase === 'generating' && '生成中...'}
                                {phase === 'done' && '✅ 完成'}
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center space-x-1">
                        <button onClick={() => setShowMaterialPanel(!showMaterialPanel)}
                            className={`flex items-center space-x-1 text-[11px] px-2.5 py-1.5 rounded-md font-bold transition-all ${showMaterialPanel
                                    ? 'bg-orange-500/20 border border-orange-500/40 text-orange-300'
                                    : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'
                                }`}
                            title="素材库管理">
                            <Package size={13} />
                            <span>素材库</span>
                        </button>
                        <button onClick={reset} className="text-zinc-500 hover:text-zinc-300 transition-colors p-1.5 rounded hover:bg-zinc-800" title="重新开始">
                            <RotateCcw size={14} />
                        </button>
                    </div>
                </div>

                {/* Hidden file inputs — must be outside conditional so refs always exist */}
                <input ref={fileInputRef} type="file" accept=".docx" className="hidden"
                    onChange={(e) => { const f = e.target.files[0]; if (f) handleTenderUpload(f); e.target.value = ''; }} />
                <input ref={materialInputRef} type="file" accept=".docx" multiple className="hidden"
                    onChange={(e) => { handleMaterialUpload(Array.from(e.target.files)); e.target.value = ''; }} />

                {/* ── Material Panel (replaces main content when active) ── */}
                {showMaterialPanel ? (
                    <MaterialPanel onClose={() => setShowMaterialPanel(false)} />
                ) : phase === 'idle' ? (
                    /* ── Upload Landing ── */
                    <div className="flex-1 flex items-center justify-center px-6"
                        onDragOver={(e) => { e.preventDefault(); e.currentTarget.querySelector('.drop-zone')?.classList.add('border-orange-400', 'bg-orange-500/5'); }}
                        onDragLeave={(e) => { e.preventDefault(); e.currentTarget.querySelector('.drop-zone')?.classList.remove('border-orange-400', 'bg-orange-500/5'); }}
                        onDrop={(e) => { e.preventDefault(); e.currentTarget.querySelector('.drop-zone')?.classList.remove('border-orange-400', 'bg-orange-500/5'); const f = e.dataTransfer.files[0]; if (f && f.name.endsWith('.docx')) handleTenderUpload(f); else if (f) alert('请上传 .docx 格式文件'); }}>
                        <div className="w-full max-w-lg text-center space-y-5">
                            <div className="w-16 h-16 bg-orange-500/10 rounded-2xl flex items-center justify-center mx-auto">
                                <Upload size={28} className="text-orange-400" />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-zinc-100">上传招标文件</h3>
                                <p className="text-[11px] text-zinc-500 mt-1">
                                    支持 .docx 格式，AI 将解析文档结构并提取投标要求
                                </p>
                            </div>
                            <div className="drop-zone border-2 border-dashed border-zinc-700 rounded-xl p-10 cursor-pointer hover:border-orange-400 hover:bg-orange-500/5 transition-all"
                                onClick={() => fileInputRef.current?.click()}>
                                <FileText size={36} className="mx-auto text-zinc-600 mb-3" />
                                <p className="text-sm text-zinc-400">点击选择文件或拖拽到此处</p>
                                <p className="text-[10px] text-zinc-600 mt-1">.docx 招标文件</p>
                            </div>
                            <div className="flex items-center justify-center space-x-6 text-[10px] text-zinc-600">
                                <span className="flex items-center space-x-1"><Sparkles size={10} className="text-orange-400" /><span>Qwen-Max 智能分类</span></span>
                                <span className="flex items-center space-x-1"><FileText size={10} className="text-emerald-400" /><span>BGE 语义检索</span></span>
                                <span className="flex items-center space-x-1"><CheckCircle size={10} className="text-blue-400" /><span>自动校验</span></span>
                            </div>
                        </div>
                    </div>
                ) : (
                    /* ── Chat Messages ── */
                    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
                        {messages.map((msg, i) => (
                            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`max-w-[85%] rounded-lg px-3.5 py-2.5 ${msg.role === 'user'
                                    ? 'bg-orange-500/20 border border-orange-500/30 text-orange-200'
                                    : 'bg-zinc-800/80 border border-zinc-700/50'
                                    }`}>
                                    {msg.role === 'ai' && msg.type === 'stream' ? (
                                        <div className="font-mono text-[11px] leading-relaxed space-y-0.5">
                                            {renderContent(msg)}
                                            {processing && (
                                                <div className="text-zinc-600 animate-pulse mt-1">{'>'} █</div>
                                            )}
                                        </div>
                                    ) : msg.role === 'ai' && msg.type === 'action' ? (
                                        <div className="text-[12px] text-zinc-200 space-y-2">
                                            <p>{msg.content}</p>
                                            {msg.actions ? (
                                                <div className="flex items-center space-x-2">
                                                    {msg.actions.map((act, ai) => (
                                                        <button key={ai}
                                                            onClick={() => {
                                                                if (act.action === 'confirm_materials') confirmMaterials(act.uploadId);
                                                                else if (act.action === 'skip_materials') addMsg('ai', '⏭️ 已跳过，素材未入库');
                                                                else if (act.action === 'show_structure') setShowStructure(true);
                                                            }}
                                                            disabled={processing}
                                                            className="flex items-center space-x-1.5 px-4 py-2 rounded-md text-[11px] font-bold bg-orange-500/20 border border-orange-500/40 text-orange-300 hover:bg-orange-500/30 transition-all disabled:opacity-40">
                                                            <span>{act.label}</span>
                                                        </button>
                                                    ))}
                                                </div>
                                            ) : (
                                                <button onClick={() => setShowStructure(true)}
                                                    className="flex items-center space-x-1.5 px-4 py-2 rounded-md text-[11px] font-bold bg-orange-500/20 border border-orange-500/40 text-orange-300 hover:bg-orange-500/30 transition-all">
                                                    <Eye size={12} />
                                                    <span>📋 查看文件结构</span>
                                                </button>
                                            )}
                                        </div>
                                    ) : (
                                        <div className="text-[12px] leading-relaxed whitespace-pre-wrap">
                                            {msg.role === 'ai' ? (
                                                <div className="text-zinc-200">{renderContent(msg)}</div>
                                            ) : (
                                                <span>{msg.content}</span>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                        <div ref={chatEndRef} />
                    </div>
                )}

                {/* ── Bottom Action Bar (only in chat mode) ── */}
                {phase !== 'idle' && (
                    <div className="shrink-0 border-t border-zinc-800 bg-zinc-900/90 backdrop-blur px-4 py-3">
                        <div className="flex items-center space-x-2">
                            {/* Upload tender file */}
                            <button onClick={() => fileInputRef.current?.click()}
                                disabled={processing}
                                className="flex items-center space-x-1.5 px-3 py-2 rounded-md text-[11px] font-bold bg-zinc-800 border border-zinc-700 text-zinc-300 hover:bg-zinc-700 hover:text-white transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                                title="上传招标文件">
                                <Upload size={12} />
                                <span>上传招标</span>
                            </button>

                            {/* Upload material */}
                            <button onClick={() => materialInputRef.current?.click()}
                                disabled={processing || !taskId}
                                className="flex items-center space-x-1.5 px-3 py-2 rounded-md text-[11px] font-bold bg-zinc-800 border border-zinc-700 text-zinc-300 hover:bg-zinc-700 hover:text-white transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                                title="上传素材">
                                <FileText size={12} />
                                <span>上传素材</span>
                            </button>

                            {/* Fill demo */}
                            <button onClick={fillDemo}
                                disabled={processing}
                                className="flex items-center space-x-1.5 px-3 py-2 rounded-md text-[11px] font-bold bg-zinc-800 border border-zinc-700 text-orange-400 hover:bg-orange-500/10 hover:border-orange-500/30 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                                title="填充天元律所数据">
                                <Sparkles size={12} />
                                <span>天元数据</span>
                            </button>

                            {/* View Structure */}
                            {requirements && (
                                <button onClick={() => setShowStructure(true)}
                                    className="flex items-center space-x-1.5 px-3 py-2 rounded-md text-[11px] font-bold bg-zinc-800 border border-zinc-700 text-zinc-300 hover:bg-zinc-700 hover:text-white transition-all">
                                    <Eye size={12} />
                                    <span>查看结构</span>
                                </button>
                            )}

                            {/* Spacer */}
                            <div className="flex-1" />

                            {/* Generate */}
                            {phase === 'ready' && (
                                <button onClick={startGeneration}
                                    disabled={processing}
                                    className="flex items-center space-x-1.5 px-5 py-2 rounded-md text-[11px] font-bold bg-orange-500 text-white hover:bg-orange-600 shadow-lg shadow-orange-500/20 transition-all disabled:opacity-40 disabled:cursor-not-allowed">
                                    <Sparkles size={12} />
                                    <span>开始生成</span>
                                </button>
                            )}

                            {/* Download */}
                            {phase === 'done' && (
                                <button onClick={handleDownload}
                                    className="flex items-center space-x-1.5 px-5 py-2 rounded-md text-[11px] font-bold bg-emerald-500 text-white hover:bg-emerald-600 shadow-lg shadow-emerald-500/20 transition-all">
                                    <Download size={12} />
                                    <span>下载 .docx</span>
                                </button>
                            )}
                        </div>
                        <p className="text-[9px] text-zinc-600 mt-1.5 text-center">
                            拖拽 .docx 文件到对话区域即可上传 · Powered by Qwen-Max + BGE
                        </p>
                    </div>
                )}
            </div>

            {showStructure && requirements && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setShowStructure(false)}>
                    <div className="bg-white w-full max-w-3xl max-h-[80vh] rounded-lg shadow-2xl overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()} style={{ fontFamily: '"SimSun", "宋体", "Songti SC", serif' }}>
                        {/* Modal header */}
                        <div className="flex items-center justify-between px-10 py-4 border-b-2 border-red-700">
                            <div className="text-center flex-1">
                                <h1 style={{ fontFamily: '"SimHei", "黑体", "Heiti SC", sans-serif', fontSize: '20px', fontWeight: 'bold', color: '#1a1a1a' }}>
                                    {requirements?.bid_title || '投标文件'}
                                </h1>
                                <p className="text-xs text-gray-500 mt-1">目 录</p>
                            </div>
                            <button onClick={() => setShowStructure(false)} className="text-gray-400 hover:text-gray-600 p-1 rounded hover:bg-gray-100 transition-colors">
                                <X size={18} />
                            </button>
                        </div>
                        {/* Scrollable TOC */}
                        <div className="flex-1 overflow-y-auto px-10 py-4">
                            {requirements?.volumes?.map((vol, vi) => (
                                <div key={vi}>
                                    {(vol.sections || []).map((sec, si) => {
                                        const typeLabel = { narrative: '叙述', table: '表格', form: '表单', qualification: '资质' };
                                        const typeColor = { narrative: 'bg-blue-50 text-blue-600 border-blue-200', table: 'bg-emerald-50 text-emerald-600 border-emerald-200', form: 'bg-amber-50 text-amber-600 border-amber-200', qualification: 'bg-purple-50 text-purple-600 border-purple-200' };
                                        return (
                                            <div key={si} className="flex items-center py-1.5 border-b border-gray-100 hover:bg-gray-50 transition-colors">
                                                <span className="text-gray-400 text-[11px] w-8 text-right mr-3 shrink-0" style={{ fontFamily: 'sans-serif' }}>{sec.order || si + 1}</span>
                                                <span className="flex-1 text-[13px] text-gray-800 leading-snug">{sec.title}</span>
                                                <span className={`text-[9px] px-1.5 py-0.5 rounded border ml-2 shrink-0 ${typeColor[sec.type] || 'bg-gray-50 text-gray-500 border-gray-200'}`} style={{ fontFamily: 'sans-serif' }}>
                                                    {typeLabel[sec.type] || sec.type}
                                                </span>
                                            </div>
                                        );
                                    })}
                                </div>
                            ))}
                        </div>
                        {/* Stats footer */}
                        <div className="px-10 py-3 border-t border-gray-200 bg-gray-50 flex items-center justify-between text-[10px] text-gray-500" style={{ fontFamily: 'sans-serif' }}>
                            <div className="flex space-x-4">
                                <span>📝 叙述 {requirements?.volumes?.reduce((s, v) => s + (v.sections || []).filter(x => x.type === 'narrative').length, 0)}</span>
                                <span>📊 表格 {requirements?.volumes?.reduce((s, v) => s + (v.sections || []).filter(x => x.type === 'table').length, 0)}</span>
                                <span>📋 表单 {requirements?.volumes?.reduce((s, v) => s + (v.sections || []).filter(x => x.type === 'form').length, 0)}</span>
                                <span>🏅 资质 {requirements?.volumes?.reduce((s, v) => s + (v.sections || []).filter(x => x.type === 'qualification').length, 0)}</span>
                            </div>
                            <span>共 {requirements?.volumes?.reduce((s, v) => s + (v.sections?.length || 0), 0)} 个章节</span>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
