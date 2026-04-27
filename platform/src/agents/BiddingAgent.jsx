import { useState, useRef, useEffect } from 'react';
import { FileText, Loader2, CheckCircle, Download, Upload, Sparkles, RotateCcw, Send, AlertTriangle, ChevronDown, Eye, X, Package, Lock, Unlock, RefreshCw } from 'lucide-react';
import MaterialPanel from './MaterialPanel';

const API_BASE = `http://${window.location.hostname}:8001`;

export default function BiddingAgent() {
    const [messages, setMessages] = useState([
        { role: 'ai', content: '👋 欢迎使用智能投标文件生成系统。请上传招标文件 (.docx)，我将解析结构并生成完整投标文件。', type: 'text', time: new Date() },
    ]);
    const [taskId, setTaskId] = useState(null);
    const [requirements, setRequirements] = useState(null);
    const [outputFilename, setOutputFilename] = useState('');
    const [processing, setProcessing] = useState(false);  // true when AI is working
    const [phase, setPhase] = useState('idle'); // idle | parsing | confirming | material_selection | generating | done
    const [showStructure, setShowStructure] = useState(false);
    const [showMaterialPanel, setShowMaterialPanel] = useState(false);
    const [sectionChecked, setSectionChecked] = useState({}); // { "vi-si": true/false }
    const [parseProgress, setParseProgress] = useState({ step: 0, startTime: null }); // parsing phase progress
    const [genProgress, setGenProgress] = useState({ total: 0, done: 0, current: '', sections: {} }); // per-section status
    const [liveContent, setLiveContent] = useState({ title: '', text: '', index: 0 }); // streaming content preview
    const [completedSections, setCompletedSections] = useState({}); // { title: content } for review
    const [viewingSection, setViewingSection] = useState(null); // title of section user is viewing
    const [lockedSections, setLockedSections] = useState({}); // { title: true } - locked sections won't be regenerated
    const [regenerating, setRegenerating] = useState(null); // title of section being regenerated
    const [expandedDoneSection, setExpandedDoneSection] = useState(null); // which section is expanded in done page

    // Material selection state
    const [selectedCompany, setSelectedCompany] = useState('');
    const [companies, setCompanies] = useState([]);
    const [bidProjectList, setBidProjectList] = useState([]); // projects under selected company
    const [selectedProjectId, setSelectedProjectId] = useState(null); // selected project id
    const [materialPreview, setMaterialPreview] = useState(null);
    const [loadingPreview, setLoadingPreview] = useState(false);

    // Company data for generation
    const [companyData, setCompanyData] = useState({
        company_name: '', legal_rep: '', license_no: '', address: '',
        phone: '', email: '', established_year: '', lawyer_count: '',
        partner_count: '', registered_capital: '',
    });

    const fileInputRef = useRef(null);
    const materialInputRef = useRef(null);
    const chatEndRef = useRef(null);
    const contentEndRef = useRef(null);
    const abortRef = useRef(null);

    // Auto-scroll to bottom when messages change
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Auto-scroll live content panel
    useEffect(() => {
        contentEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [liveContent.text, viewingSection]);

    // Tick timer during parsing phase for live elapsed display
    const [, setTick] = useState(0);
    useEffect(() => {
        if (phase !== 'parsing') return;
        const t = setInterval(() => setTick(n => n + 1), 1000);
        return () => clearInterval(t);
    }, [phase]);

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
        setParseProgress({ step: 0, startTime: Date.now() });

        // Start streaming AI log
        setMessages(prev => [...prev, { role: 'ai', content: '', type: 'stream', time: new Date() }]);

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('llm_provider', 'qwen');

            const uploadUrl = `${API_BASE}/api/bidding/parse-structure`;
            console.log('[BiddingAgent] 📤 Uploading to:', uploadUrl, '| File:', file.name, file.size, 'bytes');

            const res = await fetch(uploadUrl, {
                method: 'POST', body: formData,
            });
            console.log('[BiddingAgent] 📥 Response:', res.status, res.statusText);

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
                            // Track steps based on log content
                            if (ev.message?.includes('文件已保存')) setParseProgress(p => ({ ...p, step: 1 }));
                            if (ev.message?.includes('文档解析完成')) setParseProgress(p => ({ ...p, step: 2 }));
                            if (ev.message?.includes('分析完成')) setParseProgress(p => ({ ...p, step: 3 }));
                        } else if (ev.type === 'phase') {
                            updateLastAiMsg(ev.message);
                            if (ev.phase === 'analyzing') setParseProgress(p => ({ ...p, step: 2 }));
                        } else if (ev.type === 'heartbeat') {
                            // SSE keep-alive, ignore
                        } else if (ev.type === 'section') {
                            updateLastAiMsg(`   ${ev.icon || '📄'} ${ev.title}  → ${ev.type}`);
                        } else if (ev.type === 'complete') {
                            setTaskId(ev.task_id);
                            setRequirements(ev.requirements);

                            // Initialize all sections as checked
                            const checks = {};
                            (ev.requirements?.volumes || []).forEach((v, vi) => {
                                (v.sections || []).forEach((_, si) => {
                                    checks[`${vi}-${si}`] = true;
                                });
                            });
                            setSectionChecked(checks);
                            setPhase('confirming');

                            const vols = ev.requirements?.volumes || [];
                            const totalSecs = vols.reduce((s, v) => s + (v.sections?.length || 0), 0);
                            updateLastAiMsg(`\n✅ 解析完成! 共 ${totalSecs} 个章节`);
                            addMsg('ai', `招标文件解析完成，请确认结构后开始生成。`, 'action');
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
                body: JSON.stringify({
                    upload_id: uploadId,
                    company: selectedCompany || '',
                }),
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

    // ── Start generation → SSE stream with live content ──
    const startGeneration = async () => {
        if (!taskId) return;

        // Count selected sections
        const checkedCount = Object.values(sectionChecked).filter(Boolean).length;
        addMsg('user', `▶️ 开始生成投标文件 (${checkedCount} 章节)`);
        setProcessing(true);
        setPhase('generating');

        // Initialize progress tracking
        const initSections = {};
        (requirements?.volumes || []).forEach((v, vi) => {
            (v.sections || []).forEach((sec, si) => {
                if (sectionChecked[`${vi}-${si}`]) {
                    initSections[sec.title] = { status: 'pending', chars: 0 };
                }
            });
        });
        setGenProgress({ total: checkedCount, done: 0, current: '', sections: initSections });
        setLiveContent({ title: '', text: '', index: 0 });
        setCompletedSections({});
        setViewingSection(null);

        // Accumulate streaming content locally (not via state to avoid re-render storm)
        const contentAcc = {};  // { sectionTitle: text }
        const completedAcc = {}; // { sectionTitle: fullContent }
        let genStartTime = Date.now();

        try {
            // Use selectedCompany and selectedProjectId directly
            const effectiveCompanyData = { ...companyData, company_name: selectedCompany || companyData.company_name };
            const res = await fetch(`${API_BASE}/api/bidding/generate-full/${taskId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ company_data: effectiveCompanyData, llm_provider: 'qwen', project_id: selectedProjectId }),
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
                            setGenProgress(p => ({ ...p, total: ev.total_sections, cached: ev.cached_sections || 0 }));
                        } else if (ev.type === 'progress') {
                            contentAcc[ev.section_title] = ''; // start accumulating
                            setLiveContent({ title: ev.section_title, text: '', index: ev.current });
                            setGenProgress(p => ({
                                ...p, current: ev.section_title,
                                sections: { ...p.sections, [ev.section_title]: { status: 'generating', chars: 0 } },
                            }));
                        } else if (ev.type === 'content_chunk') {
                            // Real-time streaming content
                            const t = ev.section_title;
                            contentAcc[t] = (contentAcc[t] || '') + ev.chunk;
                            setLiveContent(prev => (
                                prev.title === t
                                    ? { ...prev, text: contentAcc[t] }
                                    : { title: t, text: contentAcc[t], index: ev.current }
                            ));
                        } else if (ev.type === 'section_done') {
                            doneCount++;
                            completedAcc[ev.section_title] = ev.content || contentAcc[ev.section_title] || '';
                            setCompletedSections(prev => ({ ...prev, [ev.section_title]: completedAcc[ev.section_title] }));
                            setGenProgress(p => {
                                const newSections = { ...p.sections, [ev.section_title]: { status: ev.status === 'error' ? 'error' : 'done', chars: ev.content_length || 0, elapsed: ev.elapsed } };
                                // Calculate ETA from non-cached section elapsed times
                                const genElapsed = Object.values(newSections).filter(s => s.status === 'done' && s.elapsed).map(s => s.elapsed);
                                const avgTime = genElapsed.length > 0 ? genElapsed.reduce((a, b) => a + b, 0) / genElapsed.length : 0;
                                const remaining = p.total - doneCount;
                                const etaSeconds = Math.round(avgTime * remaining);
                                return { ...p, done: doneCount, elapsed: ((Date.now() - genStartTime) / 1000).toFixed(0), sections: newSections, etaSeconds, avgSectionTime: avgTime.toFixed(1) };
                            });
                        } else if (ev.type === 'section_cached') {
                            doneCount++;
                            completedAcc[ev.section_title] = ev.content || '';
                            setCompletedSections(prev => ({ ...prev, [ev.section_title]: ev.content || '' }));
                            setGenProgress(p => {
                                const newSections = { ...p.sections, [ev.section_title]: { status: 'cached', chars: (ev.content || '').length, elapsed: ev.elapsed } };
                                const remaining = p.total - doneCount;
                                // Recalculate ETA (cached sections don't affect avg)
                                const genElapsed = Object.values(newSections).filter(s => s.status === 'done' && s.elapsed).map(s => s.elapsed);
                                const avgTime = genElapsed.length > 0 ? genElapsed.reduce((a, b) => a + b, 0) / genElapsed.length : 0;
                                const etaSeconds = Math.round(avgTime * remaining);
                                return { ...p, done: doneCount, sections: newSections, etaSeconds, avgSectionTime: avgTime.toFixed(1) };
                            });
                        } else if (ev.type === 'section_error') {
                            doneCount++;
                            setGenProgress(p => ({
                                ...p, done: doneCount,
                                sections: { ...p.sections, [ev.section_title]: { status: 'error', chars: 0, error: ev.error, elapsed: ev.elapsed } },
                            }));
                        } else if (ev.type === 'assembling') {
                            setGenProgress(p => ({ ...p, current: '📦 组装文件...' }));
                            setLiveContent({ title: '📦 正在组装 Word 文档...', text: '', index: 0 });
                        } else if (ev.type === 'complete') {
                            setOutputFilename(ev.file_path);
                            setGenProgress(p => ({
                                ...p, current: '✅ 完成',
                                totalElapsed: ev.total_elapsed,
                                verification: ev.verification,
                            }));
                            setPhase('done');
                        }
                    } catch { }
                }
            }
        } catch (err) {
            addMsg('ai', '❌ 生成失败: ' + err.message);
            setPhase('confirming');
        } finally {
            setProcessing(false);
        }
    };

    // ── Regenerate single section ──
    const regenerateSection = async (sectionTitle) => {
        if (!taskId || regenerating) return;
        setRegenerating(sectionTitle);
        try {
            const effectiveCompanyData = { ...companyData, company_name: selectedCompany || companyData.company_name };
            const res = await fetch(`${API_BASE}/api/bidding/regenerate-section/${taskId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    section_title: sectionTitle,
                    company_data: effectiveCompanyData,
                    llm_provider: 'qwen',
                    project_id: selectedProjectId,
                }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let accumulated = '';

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
                        if (ev.type === 'content_chunk') {
                            accumulated += ev.chunk;
                            setCompletedSections(prev => ({ ...prev, [sectionTitle]: accumulated }));
                        } else if (ev.type === 'section_done') {
                            const finalContent = ev.content || accumulated;
                            setCompletedSections(prev => ({ ...prev, [sectionTitle]: finalContent }));
                            setGenProgress(p => ({
                                ...p,
                                sections: {
                                    ...p.sections,
                                    [sectionTitle]: { ...p.sections[sectionTitle], status: 'done', chars: finalContent.length },
                                },
                            }));
                        }
                    } catch {}
                }
            }
        } catch (err) {
            addMsg('ai', `❌ 重新生成失败: ${err.message}`);
        } finally {
            setRegenerating(null);
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
        setSectionChecked({});
        setGenProgress({ total: 0, done: 0, current: '', sections: {} });
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
                                {phase === 'confirming' && `大纲确认 · ${requirements?.volumes?.reduce((s, v) => s + (v.sections?.length || 0), 0) || 0} 章节`}
                                {phase === 'material_selection' && '选择投标主体'}
                                {phase === 'generating' && `生成中 ${genProgress.done}/${genProgress.total}`}
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

                {/* ── Step Bar (visible after parsing) ── */}
                {['confirming', 'material_selection', 'generating', 'done'].includes(phase) && (
                    <div className="flex items-center px-4 py-1.5 border-b border-zinc-800 bg-zinc-900/60 gap-1">
                        {[
                            { key: 'confirming', label: '大纲确认', icon: '📋', phase: 'confirming' },
                            { key: 'material_selection', label: '素材匹配', icon: '🔗', phase: 'material_selection' },
                            { key: 'generating', label: '文件生成', icon: '⚡', phase: 'generating' },
                        ].map((step, i, arr) => {
                            const phaseOrder = { confirming: 0, material_selection: 1, generating: 2, done: 2 };
                            const currentIdx = phaseOrder[phase] ?? 0;
                            const stepIdx = i;
                            const isActive = step.phase === phase || (phase === 'done' && step.key === 'generating');
                            const isDone = stepIdx < currentIdx || phase === 'done';
                            const canClick = isDone && !processing;
                            return (
                                <div key={step.key} className="flex items-center gap-1">
                                    <button
                                        onClick={() => canClick && setPhase(step.phase)}
                                        disabled={!canClick}
                                        className={`flex items-center gap-1 text-[10px] px-2 py-1 rounded-md transition-all ${
                                            isActive
                                                ? 'bg-orange-500/20 border border-orange-500/40 text-orange-300 font-bold'
                                                : isDone
                                                    ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 cursor-pointer hover:bg-emerald-500/20'
                                                    : 'bg-zinc-800/50 border border-zinc-700/50 text-zinc-600'
                                        }`}>
                                        <span>{isDone && !isActive ? '✓' : step.icon}</span>
                                        <span>{step.label}</span>
                                    </button>
                                    {i < arr.length - 1 && (
                                        <div className={`w-4 h-px ${
                                            stepIdx < currentIdx || phase === 'done' ? 'bg-emerald-500/40' : 'bg-zinc-700'
                                        }`} />
                                    )}
                                </div>
                            );
                        })}
                        {phase === 'done' && (
                            <span className="ml-auto text-[10px] text-emerald-400 font-bold">✅ 完成</span>
                        )}
                    </div>
                )}

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
                ) : phase === 'confirming' && requirements ? (
                    /* ══════════════════════════════════════════════════════════ */
                    /* ── STEP 2: Structure Confirmation — Two Panel Layout ──── */
                    /* ══════════════════════════════════════════════════════════ */
                    <div className="flex-1 flex overflow-hidden">
                        {/* ── Left Panel: Word-Style Document Preview ── */}
                        <div className="flex-1 overflow-y-auto p-6 bg-zinc-800/30">
                            <div className="max-w-[560px] mx-auto bg-white rounded shadow-2xl shadow-black/40 text-black"
                                style={{ minHeight: '700px' }}>
                                {/* Cover page */}
                                <div className="px-10 pt-16 pb-8 border-b-2 border-gray-200">
                                    <p className="text-center text-gray-400 text-[10px] tracking-[0.5em] mb-6">投 标 文 件</p>
                                    <h1 className="text-center text-[18px] font-bold text-gray-900 leading-relaxed mb-3">
                                        {requirements?.bid_title || '投标文件'}
                                    </h1>
                                    <p className="text-center text-gray-400 text-[11px] mb-8">（商务技术部分）</p>
                                    <div className="w-40 mx-auto border-t border-gray-300 my-4"></div>
                                    <div className="text-center space-y-1 mt-6">
                                        <p className="text-gray-500 text-[11px]">投标人：{requirements?.company_name || '________'}</p>
                                        <p className="text-gray-500 text-[11px]">日期：{new Date().toLocaleDateString('zh-CN')}</p>
                                    </div>
                                </div>

                                {/* Document outline */}
                                <div className="px-10 py-6 space-y-1">
                                    <h2 className="text-center text-[13px] font-bold text-gray-800 tracking-[0.4em] mb-5">目    录</h2>
                                    {requirements?.volumes?.map((vol, vi) =>
                                        (vol.sections || []).map((sec, si) => {
                                            const key = `${vi}-${si}`;
                                            const checked = sec.rejection_risk ? true : sectionChecked[key] !== false;
                                            const isRejection = sec.rejection_risk === true;
                                            const outline = sec.content_outline || [];
                                            const matRefs = sec.material_refs || [];
                                            const typeLabel = { narrative: '方案', table: '表格', form: '表单', qualification: '证照' };
                                            const typeColor = {
                                                narrative: 'text-blue-600 bg-blue-50',
                                                table: 'text-emerald-600 bg-emerald-50',
                                                form: 'text-amber-600 bg-amber-50',
                                                qualification: 'text-purple-600 bg-purple-50',
                                            };

                                            return (
                                                <div key={`outline-${key}`}
                                                    className={`transition-opacity ${checked ? '' : 'opacity-30'}`}>
                                                    {/* Section title row */}
                                                    <div className="flex items-baseline py-1.5 group">
                                                        <span className="text-gray-400 w-6 text-right mr-2 text-[11px] shrink-0 font-mono">{sec.order || si + 1}.</span>
                                                        <span className={`text-[12px] font-bold flex-1 ${isRejection ? 'text-red-700' : 'text-gray-900'} ${!checked ? 'line-through' : ''}`}>
                                                            {sec.title}
                                                        </span>
                                                        {isRejection && (
                                                            <span className="text-[8px] px-1.5 py-0.5 rounded-sm bg-red-50 text-red-500 border border-red-200 shrink-0 ml-2 font-bold">废标</span>
                                                        )}
                                                        {(sec.linked_total_score || sec.score_weight || 0) > 0 && (
                                                            <span className="text-[8px] px-1.5 py-0.5 rounded-sm bg-blue-50 text-blue-600 border border-blue-200 shrink-0 ml-1">{sec.linked_total_score || sec.score_weight}分</span>
                                                        )}
                                                        <span className={`text-[8px] px-1.5 py-0.5 rounded-sm shrink-0 ml-1 ${typeColor[sec.type] || 'text-gray-500 bg-gray-50'}`}>
                                                            {typeLabel[sec.type] || sec.type}
                                                        </span>
                                                    </div>

                                                    {/* Content outline bullets */}
                                                    {checked && outline.length > 0 && (
                                                        <div className="ml-8 mb-2 pl-3 border-l-2 border-gray-200 space-y-0.5">
                                                            {outline.map((point, pi) => (
                                                                <div key={pi} className="text-[10px] text-gray-500 leading-snug flex items-start">
                                                                    <span className="text-gray-300 mr-1.5 mt-0.5 shrink-0">›</span>
                                                                    <span>{point}</span>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}

                                                    {/* Material references */}
                                                    {checked && matRefs.length > 0 && (
                                                        <div className="ml-8 mb-2 flex flex-wrap gap-1">
                                                            {matRefs.map((ref, ri) => (
                                                                <span key={ri} className="text-[8px] px-1.5 py-0.5 rounded bg-orange-50 text-orange-600 border border-orange-200">
                                                                    📎 {ref}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    )}

                                                    {/* Linked scoring items */}
                                                    {checked && (sec.linked_scoring || []).length > 0 && (
                                                        <div className="ml-8 mb-2 pl-3 border-l-2 border-blue-200 space-y-1">
                                                            {sec.linked_scoring.map((sc, sci) => (
                                                                <div key={sci}>
                                                                    <div className="text-[10px] text-blue-700 font-medium flex items-center gap-1">
                                                                        <span>🏆</span>
                                                                        <span>{sc.item}</span>
                                                                        <span className="text-[8px] px-1 py-0.5 rounded bg-blue-50 text-blue-500 border border-blue-200">{sc.max_score}分</span>
                                                                    </div>
                                                                    {(sc.sub_criteria || []).length > 0 && (
                                                                        <div className="ml-4 mt-0.5 space-y-0.5">
                                                                            {sc.sub_criteria.map((sub, subi) => (
                                                                                <div key={subi} className="text-[9px] text-gray-500 flex items-start">
                                                                                    <span className="text-blue-300 mr-1 shrink-0">├─</span>
                                                                                    <span>{sub.name || sub.item} {sub.score > 0 ? `${sub.score}分` : ''}</span>
                                                                                    {sub.scoring_rule && (
                                                                                        <span className="text-gray-400 ml-1">({sub.scoring_rule})</span>
                                                                                    )}
                                                                                </div>
                                                                            ))}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}

                                                    {/* Linked rejection items */}
                                                    {checked && (sec.linked_rejection || []).length > 0 && (
                                                        <div className="ml-8 mb-2 pl-3 border-l-2 border-red-200 space-y-0.5">
                                                            {sec.linked_rejection.map((rj, rji) => (
                                                                <div key={rji} className="text-[9px] text-red-600 flex items-start">
                                                                    <span className="mr-1 shrink-0">🔴</span>
                                                                    <span>{rj.condition}</span>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* ── Right Panel: Controls ── */}
                        <div className="w-[440px] shrink-0 border-l border-zinc-800 flex flex-col overflow-hidden bg-zinc-900/80">
                            {/* Header */}
                            <div className="px-4 py-3 border-b border-zinc-800">
                                <h2 className="text-[14px] font-bold text-zinc-100 flex items-center space-x-2">
                                    <Eye size={16} className="text-orange-400" />
                                    <span>投标文件大纲</span>
                                </h2>
                                <p className="text-[11px] text-zinc-500 mt-1">
                                    审阅内容大纲和素材引用，确认后开始制作
                                </p>
                            </div>

                            {/* Verification panel (collapsed) */}
                            {requirements?.verification && (() => {
                                const v = requirements.verification;
                                const rej = v.rejection_check || {};
                                const evl = v.evaluation_check || {};
                                const doc = v.document_check || {};
                                const fmt = v.format_info || {};
                                const dl = v.deadline_info || {};
                                return (
                                    <div className="border-b border-zinc-800">
                                        <div className="px-4 py-2 flex items-center justify-between cursor-pointer bg-gradient-to-r from-orange-500/8 to-transparent"
                                            onClick={() => {
                                                const el = document.getElementById('verification-detail');
                                                if (el) el.classList.toggle('hidden');
                                            }}>
                                            <span className="text-[12px] font-bold text-zinc-200 flex items-center gap-2">
                                                📋 招标要点分析
                                                {rej.total > 0 && (
                                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/15 text-red-400">
                                                        {rej.total}项废标条件
                                                    </span>
                                                )}
                                                {evl.total > 0 && (
                                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400">
                                                        {evl.total}项评分维度
                                                    </span>
                                                )}
                                                {doc.total > 0 && (
                                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400">
                                                        {doc.total}份文件
                                                    </span>
                                                )}
                                            </span>
                                            <span className="text-[10px] text-zinc-500">收起/展开 ▼</span>
                                        </div>

                                        <div id="verification-detail" className="px-4 py-3 space-y-3 border-t border-zinc-800 max-h-[350px] overflow-y-auto">
                                            {rej.total > 0 && (
                                                <div>
                                                    <div className="text-[11px] font-bold text-red-400 mb-1.5">🔴 废标条件 — 以下情形将导致投标无效</div>
                                                    {(rej.items || []).map((item, i) => (
                                                        <div key={i} className="flex items-start gap-2 text-[10px] py-1 pl-3 border-l-2 border-red-500/20 mb-0.5">
                                                            <span className="text-red-400/70 shrink-0">{i + 1}.</span>
                                                            <span className="text-zinc-300">{item.condition}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                            {evl.total > 0 && (
                                                <div>
                                                    <div className="text-[11px] font-bold text-blue-400 mb-1.5">📊 评分维度 — 评标打分依据 ({evl.covered}/{evl.total} 已覆盖)</div>
                                                    {(evl.items || []).map((item, i) => {
                                                        const isMissing = item.status === 'missing';
                                                        const subs = item.sub_criteria || [];
                                                        return (
                                                            <div key={i} className={`mb-2 pl-3 border-l-2 ${isMissing ? 'border-red-500/30' : 'border-blue-500/20'}`}>
                                                                <div className="flex items-center gap-2 text-[10px] py-0.5">
                                                                    <span className={`shrink-0 ${isMissing ? 'text-red-400' : 'text-emerald-400'}`}>{isMissing ? '✗' : '✓'}</span>
                                                                    <span className={`font-bold ${isMissing ? 'text-red-300' : 'text-zinc-200'}`}>{item.item}</span>
                                                                    {item.max_score > 0 && <span className="text-blue-400 font-bold">({item.max_score}分)</span>}
                                                                    {isMissing && <span className="text-[8px] px-1 py-0.5 rounded bg-red-500/15 text-red-400 border border-red-500/30 font-bold">未覆盖</span>}
                                                                </div>
                                                                {/* Sub-criteria tree */}
                                                                {subs.length > 0 && (
                                                                    <div className="ml-4 mt-0.5 space-y-0.5">
                                                                        {subs.map((sub, si) => (
                                                                            <div key={si} className="text-[9px] text-zinc-400 flex items-start gap-1">
                                                                                <span className="text-zinc-600 shrink-0">›</span>
                                                                                <span className="text-zinc-300">{sub.name}</span>
                                                                                {sub.score > 0 && <span className="text-blue-400/70 shrink-0">({sub.score}分)</span>}
                                                                                {sub.scoring_rule && <span className="text-zinc-500 ml-1">— {sub.scoring_rule}</span>}
                                                                            </div>
                                                                        ))}
                                                                    </div>
                                                                )}
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            )}
                                            {doc.total > 0 && (
                                                <div>
                                                    <div className="text-[11px] font-bold text-purple-400 mb-1.5">📃 必须提供的文件清单</div>
                                                    <div className="flex flex-wrap gap-1.5">
                                                        {(doc.items || []).map((item, i) => (
                                                            <span key={i} className="text-[9px] px-2 py-1 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">{item.name}</span>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                            {(fmt.copies || fmt.binding || dl.submission_deadline) && (
                                                <div className="text-[10px] text-zinc-500 pt-2 border-t border-zinc-800/50 space-y-0.5">
                                                    {fmt.copies && <div>📐 {[fmt.copies, fmt.binding, fmt.paper_size].filter(Boolean).join(' | ')}</div>}
                                                    {dl.submission_deadline && <div>⏰ 截止: {dl.submission_deadline}</div>}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                );
                            })()}

                            {/* Section checkboxes */}
                            <div className="flex-1 overflow-y-auto px-4 py-2">
                                {/* Select all */}
                                <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-zinc-800">
                                    <label className="flex items-center space-x-2 cursor-pointer">
                                        <input type="checkbox"
                                            checked={Object.values(sectionChecked).every(Boolean)}
                                            onChange={(e) => {
                                                const newChecks = {};
                                                Object.keys(sectionChecked).forEach(k => { newChecks[k] = e.target.checked; });
                                                setSectionChecked(newChecks);
                                            }}
                                            className="w-3.5 h-3.5 rounded border-zinc-600 bg-zinc-800 text-orange-500 focus:ring-orange-500 accent-orange-500"
                                        />
                                        <span className="text-[10px] text-zinc-400 font-bold">全选 / 全不选</span>
                                    </label>
                                    <span className="text-[9px] text-zinc-600">
                                        {Object.values(sectionChecked).filter(Boolean).length}/{Object.keys(sectionChecked).length}
                                    </span>
                                </div>

                                {requirements?.volumes?.map((vol, vi) => (
                                    <div key={vi}>
                                        {(vol.sections || []).map((sec, si) => {
                                            const key = `${vi}-${si}`;
                                            const isRejectionRisk = sec.rejection_risk === true;
                                            const checked = isRejectionRisk ? true : sectionChecked[key] !== false;
                                            const outline = sec.content_outline || [];
                                            const matRefs = sec.material_refs || [];
                                            const typeLabel = { narrative: '叙述', table: '表格', form: '表单', qualification: '资质' };
                                            const typeColor = {
                                                narrative: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
                                                table: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
                                                form: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
                                                qualification: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
                                            };

                                            return (
                                                <div key={si}
                                                    className={`rounded-md mb-1 transition-all ${isRejectionRisk
                                                        ? 'bg-red-500/5 border border-red-500/20'
                                                        : checked
                                                            ? 'bg-zinc-800/50 border border-zinc-700/50'
                                                            : 'bg-zinc-900/30 border border-transparent opacity-50'
                                                        }`}>
                                                    {/* Header row with checkbox */}
                                                    <label className="flex items-center py-1.5 px-2 cursor-pointer text-[11px]">
                                                        <input type="checkbox"
                                                            checked={checked}
                                                            disabled={isRejectionRisk}
                                                            onChange={() => !isRejectionRisk && setSectionChecked(prev => ({ ...prev, [key]: !prev[key] }))}
                                                            className={`w-3.5 h-3.5 rounded border-zinc-600 bg-zinc-800 focus:ring-orange-500 shrink-0 ${isRejectionRisk ? 'accent-red-500 text-red-500' : 'accent-orange-500 text-orange-500'}`}
                                                        />
                                                        <span className="text-zinc-500 w-5 text-right mx-1.5 shrink-0 text-[10px]">{sec.order || si + 1}</span>
                                                        <span className={`flex-1 leading-snug truncate ${checked ? 'text-zinc-200' : 'text-zinc-500 line-through'}`}>
                                                            {sec.title}
                                                        </span>
                                                        {isRejectionRisk && (
                                                            <span className="text-[8px] px-1 py-0.5 rounded bg-red-500/15 text-red-400 border border-red-500/30 shrink-0 font-bold ml-1">🔴</span>
                                                        )}
                                                        {sec.score_weight > 0 && (
                                                            <span className="text-[8px] px-1 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 shrink-0 ml-1">{sec.linked_total_score || sec.score_weight}分</span>
                                                        )}
                                                        <span className={`text-[8px] px-1 py-0.5 rounded border shrink-0 ml-1 ${typeColor[sec.type] || 'bg-zinc-800 text-zinc-500 border-zinc-700'}`}>
                                                            {typeLabel[sec.type] || sec.type}
                                                        </span>
                                                        {matRefs.length > 0 && (
                                                            <span className="text-[8px] px-1 py-0.5 rounded bg-green-500/10 text-green-400 border border-green-500/20 shrink-0 ml-1">
                                                                📎{matRefs.length}
                                                            </span>
                                                        )}
                                                    </label>

                                                    {/* Expandable content_outline + material_refs */}
                                                    {checked && (outline.length > 0 || matRefs.length > 0) && (
                                                        <div className="px-3 pb-2 ml-7 space-y-1">
                                                            {outline.length > 0 && (
                                                                <div className="pl-2 border-l border-zinc-700 space-y-0.5">
                                                                    {outline.map((point, pi) => (
                                                                        <div key={pi} className="text-[9px] text-zinc-500 leading-snug flex items-start">
                                                                            <span className="text-zinc-600 mr-1 shrink-0">›</span>
                                                                            <span>{point}</span>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            )}
                                                            {matRefs.length > 0 && (
                                                                <div className="flex flex-wrap gap-1 pt-0.5">
                                                                    {matRefs.map((ref, ri) => (
                                                                        <span key={ri} className="text-[8px] px-1 py-0.5 rounded bg-orange-500/10 text-orange-400 border border-orange-500/20">
                                                                            📎 {ref}
                                                                        </span>
                                                                    ))}
                                                                </div>
                                                            )}

                                                            {/* Linked scoring items */}
                                                            {(sec.linked_scoring || []).length > 0 && (
                                                                <div className="pt-1 pl-2 border-l border-blue-500/30 space-y-1">
                                                                    {sec.linked_scoring.map((sc, sci) => (
                                                                        <div key={sci}>
                                                                            <div className="text-[9px] text-blue-400 font-medium flex items-center gap-1">
                                                                                <span>🏆</span>
                                                                                <span className="flex-1">{sc.item}</span>
                                                                                <span className="text-[8px] px-1 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">{sc.max_score}分</span>
                                                                            </div>
                                                                            {(sc.sub_criteria || []).length > 0 && (
                                                                                <div className="ml-3 mt-0.5 space-y-0.5">
                                                                                    {sc.sub_criteria.map((sub, subi) => (
                                                                                        <div key={subi} className="text-[8px] text-zinc-500 flex items-start">
                                                                                            <span className="text-blue-500/50 mr-1 shrink-0">├─</span>
                                                                                            <span className="text-zinc-400">{sub.name || sub.item} {sub.score > 0 ? `${sub.score}分` : ''}</span>
                                                                                            {sub.scoring_rule && (
                                                                                                <span className="text-zinc-600 ml-1 truncate">({sub.scoring_rule})</span>
                                                                                            )}
                                                                                        </div>
                                                                                    ))}
                                                                                </div>
                                                                            )}
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            )}

                                                            {/* Linked rejection items */}
                                                            {(sec.linked_rejection || []).length > 0 && (
                                                                <div className="pt-1 pl-2 border-l border-red-500/30 space-y-0.5">
                                                                    {sec.linked_rejection.map((rj, rji) => (
                                                                        <div key={rji} className="text-[8px] text-red-400 flex items-start">
                                                                            <span className="mr-1 shrink-0">🔴</span>
                                                                            <span>{rj.condition}</span>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                ))}
                            </div>

                            {/* Footer buttons */}
                            <div className="px-4 py-3 border-t border-zinc-800 bg-zinc-900/90 backdrop-blur space-y-2">
                                <div className="flex space-x-3 text-[9px] text-zinc-500 justify-center">
                                    <span>📝 {requirements?.volumes?.reduce((s, v) => s + (v.sections || []).filter(x => x.type === 'narrative').length, 0)}</span>
                                    <span>📊 {requirements?.volumes?.reduce((s, v) => s + (v.sections || []).filter(x => x.type === 'table').length, 0)}</span>
                                    <span>📋 {requirements?.volumes?.reduce((s, v) => s + (v.sections || []).filter(x => x.type === 'form').length, 0)}</span>
                                    <span>🏅 {requirements?.volumes?.reduce((s, v) => s + (v.sections || []).filter(x => x.type === 'qualification').length, 0)}</span>
                                </div>
                                <button onClick={async () => {
                                    // Fetch companies list and go to material_selection phase
                                    try {
                                        const res = await fetch(`${API_BASE}/api/bidding/materials/companies`);
                                        const data = await res.json();
                                        const companyList = data.data?.companies || [];
                                        setCompanies(companyList);
                                        // Auto-select first company and load its projects
                                        if (companyList.length > 0) {
                                            const first = companyList[0].name;
                                            setSelectedCompany(first);
                                            // Load projects
                                            const projRes = await fetch(`${API_BASE}/api/bidding/bid-projects?company=${encodeURIComponent(first)}`);
                                            const projData = await projRes.json();
                                            const projects = projData.data?.projects || [];
                                            setBidProjectList(projects);
                                            // Auto-select first project and load preview
                                            if (projects.length > 0) {
                                                setSelectedProjectId(projects[0].id);
                                                setLoadingPreview(true);
                                                const previewRes = await fetch(`${API_BASE}/api/bidding/preview-materials/${taskId}?company=${encodeURIComponent(first)}&project_id=${projects[0].id}`);
                                                const previewData = await previewRes.json();
                                                setMaterialPreview(previewData.data);
                                                setLoadingPreview(false);
                                            }
                                        }
                                        setPhase('material_selection');
                                    } catch (e) {
                                        console.error('[MaterialSelection] FAILED:', e);
                                        startGeneration();
                                    }
                                }}
                                    disabled={processing || Object.values(sectionChecked).filter(Boolean).length === 0}
                                    className="w-full flex items-center justify-center space-x-1.5 px-6 py-2.5 rounded-md text-[12px] font-bold bg-orange-500 text-white hover:bg-orange-600 shadow-lg shadow-orange-500/20 transition-all disabled:opacity-40 disabled:cursor-not-allowed">
                                    <Sparkles size={14} />
                                    <span>确认结构，选择投标主体</span>
                                </button>
                            </div>
                        </div>
                    </div>
                ) : phase === 'material_selection' ? (
                    /* ══════════════════════════════════════════════════════════ */
                    /*  PHASE: Material Selection                              */
                    /* ══════════════════════════════════════════════════════════ */
                    <div className="flex-1 flex flex-col overflow-hidden">
                        <div className="flex-1 overflow-y-auto p-4 space-y-4">
                            {/* Company + Project Selector */}
                            <div className="bg-zinc-900/80 backdrop-blur rounded-xl border border-zinc-800 p-4">
                                <h3 className="text-[13px] font-bold text-zinc-100 mb-3 flex items-center">
                                    <Package size={14} className="mr-2 text-orange-400" />
                                    选择投标主体
                                </h3>
                                {/* Company selector */}
                                <select
                                    value={selectedCompany}
                                    onChange={async (e) => {
                                        const company = e.target.value;
                                        setSelectedCompany(company);
                                        setSelectedProjectId(null);
                                        setBidProjectList([]);
                                        setMaterialPreview(null);
                                        if (!company) return;
                                        // Load projects for this company
                                        try {
                                            const res = await fetch(`${API_BASE}/api/bidding/bid-projects?company=${encodeURIComponent(company)}`);
                                            const data = await res.json();
                                            const projects = data.data?.projects || [];
                                            setBidProjectList(projects);
                                            // Auto-select if only one project
                                            if (projects.length === 1) {
                                                setSelectedProjectId(projects[0].id);
                                                setLoadingPreview(true);
                                                const previewRes = await fetch(`${API_BASE}/api/bidding/preview-materials/${taskId}?company=${encodeURIComponent(company)}&project_id=${projects[0].id}`);
                                                const previewData = await previewRes.json();
                                                setMaterialPreview(previewData.data);
                                                setLoadingPreview(false);
                                            }
                                        } catch (err) {
                                            console.error('Load projects failed:', err);
                                        }
                                    }}
                                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-[12px] text-zinc-100 focus:outline-none focus:border-orange-500 transition-colors mb-2"
                                >
                                    <option value="">选择公司 / 律所</option>
                                    {companies.map((c, i) => (
                                        <option key={i} value={c.name}>
                                            {c.name} ({c.total}素材)
                                        </option>
                                    ))}
                                </select>
                                {/* Project selector */}
                                {bidProjectList.length > 0 && (
                                    <select
                                        value={selectedProjectId || ''}
                                        onChange={async (e) => {
                                            const pid = parseInt(e.target.value) || null;
                                            setSelectedProjectId(pid);
                                            if (!pid) { setMaterialPreview(null); return; }
                                            setLoadingPreview(true);
                                            try {
                                                const res = await fetch(`${API_BASE}/api/bidding/preview-materials/${taskId}?company=${encodeURIComponent(selectedCompany)}&project_id=${pid}`);
                                                const data = await res.json();
                                                setMaterialPreview(data.data);
                                            } catch (err) {
                                                console.error('Preview failed:', err);
                                            }
                                            setLoadingPreview(false);
                                        }}
                                        className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2.5 text-[12px] text-zinc-100 focus:outline-none focus:border-purple-500 transition-colors"
                                    >
                                        <option value="">选择投标项目</option>
                                        {bidProjectList.map(p => (
                                            <option key={p.id} value={p.id}>
                                                📁 {p.name} ({p.material_count}素材)
                                            </option>
                                        ))}
                                    </select>
                                )}
                            </div>

                            {/* Material Preview */}
                            <div className="bg-zinc-900/80 backdrop-blur rounded-xl border border-zinc-800 p-4">
                                <h3 className="text-[13px] font-bold text-zinc-100 mb-3">📋 素材匹配预览</h3>
                                {loadingPreview ? (
                                    <div className="flex items-center justify-center py-6 text-zinc-500 text-[11px]">
                                        <Loader2 size={14} className="animate-spin mr-2" /> 加载中...
                                    </div>
                                ) : materialPreview ? (
                                    <div className="space-y-1">
                                        {/* Summary bar */}
                                        <div className="flex items-center gap-3 px-3 py-2 bg-zinc-800/60 rounded-lg mb-2 text-[10px] text-zinc-400">
                                            <span>📦 素材库: {materialPreview.store_summary?.resumes || 0}简历 · {materialPreview.store_summary?.projects || 0}业绩 · {materialPreview.store_summary?.qualifications || 0}资质</span>
                                            <span className="text-orange-400 font-bold">🎯 {materialPreview.matched_sections}/{materialPreview.total_sections} 章节匹配</span>
                                        </div>
                                        {/* Section matches */}
                                        {materialPreview.matches?.map((m, i) => (
                                            <div key={i} className={`flex items-center justify-between px-3 py-1.5 rounded text-[11px] ${m.match_summary ? 'bg-green-500/5 border border-green-500/20' : 'bg-zinc-800/30'}`}>
                                                <div className="flex items-center gap-2 flex-1 min-w-0">
                                                    <span className="text-zinc-500 w-4 text-right shrink-0">{i+1}</span>
                                                    <span className={`truncate ${m.match_summary ? 'text-zinc-200' : 'text-zinc-500'}`}>{m.title}</span>
                                                </div>
                                                <div className="flex items-center gap-1.5 shrink-0 ml-2">
                                                    {m.match_summary ? (
                                                        <span className="text-[10px] px-2 py-0.5 rounded bg-green-500/15 text-green-400 border border-green-500/30 font-medium">
                                                            {m.match_summary}
                                                        </span>
                                                    ) : (
                                                        <span className="text-[10px] text-zinc-600">{m.type === 'narrative' ? 'AI生成' : m.type === 'form' ? '模板' : m.type === 'table' ? '表格' : '资质'}</span>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="text-center py-6 text-zinc-600 text-[11px]">选择公司后查看素材匹配</div>
                                )}
                            </div>
                        </div>

                        {/* Footer */}
                        <div className="px-4 py-3 border-t border-zinc-800 bg-zinc-900/90 backdrop-blur space-y-2">
                            <div className="flex gap-2">
                                <button onClick={() => setPhase('confirming')}
                                    className="flex-1 flex items-center justify-center px-4 py-2.5 rounded-md text-[12px] font-medium bg-zinc-800 text-zinc-300 hover:bg-zinc-700 transition-colors border border-zinc-700">
                                    ← 返回大纲
                                </button>
                                <button onClick={() => {
                                    // Update companyData with selected company + project
                                    setCompanyData(prev => ({ ...prev, company_name: selectedCompany }));
                                    startGeneration();
                                }}
                                    disabled={processing || !selectedProjectId}
                                    className="flex-[2] flex items-center justify-center space-x-1.5 px-6 py-2.5 rounded-md text-[12px] font-bold bg-orange-500 text-white hover:bg-orange-600 shadow-lg shadow-orange-500/20 transition-all disabled:opacity-40 disabled:cursor-not-allowed">
                                    <Sparkles size={14} />
                                    <span>{selectedProjectId ? '开始生成投标文件' : '请先选择项目'}</span>
                                </button>
                            </div>
                        </div>
                    </div>

                ) : phase === 'generating' ? (
                    /* ══════════════════════════════════════════════════════════ */
                    /* ── STEP 3: Generation — Two-Panel Live Preview ─────── */
                    /* ══════════════════════════════════════════════════════════ */
                    <div className="flex-1 flex flex-col overflow-hidden">
                        {/* Progress header */}
                        <div className="px-6 py-3 border-b border-zinc-800 bg-zinc-900/50">
                            <div className="flex items-center justify-between">
                                <h2 className="text-sm font-bold text-zinc-100 flex items-center space-x-2">
                                    <Loader2 size={14} className="text-orange-400 animate-spin" />
                                    <span>正在生成投标文件</span>
                                    {genProgress.total > 0 && (
                                        <span className="text-[11px] font-normal text-zinc-400 ml-1">
                                            {Math.round(genProgress.done / genProgress.total * 100)}%
                                        </span>
                                    )}
                                </h2>
                                <div className="flex items-center space-x-3 text-[11px]">
                                    {genProgress.elapsed && (
                                        <span className="text-zinc-500">⏱ {genProgress.elapsed}s</span>
                                    )}
                                    {genProgress.etaSeconds > 0 && (
                                        <span className="text-zinc-400">
                                            预计还需 {genProgress.etaSeconds >= 60 ? `${Math.floor(genProgress.etaSeconds / 60)}分${genProgress.etaSeconds % 60}秒` : `${genProgress.etaSeconds}秒`}
                                        </span>
                                    )}
                                    <span className="font-bold text-orange-400">
                                        {genProgress.done} / {genProgress.total}
                                    </span>
                                </div>
                            </div>
                            <div className="mt-2 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                                <div className="h-full bg-gradient-to-r from-orange-500 to-amber-500 rounded-full transition-all duration-500"
                                    style={{ width: `${genProgress.total ? (genProgress.done / genProgress.total * 100) : 0}%` }} />
                            </div>
                            {genProgress.avgSectionTime > 0 && (
                                <div className="mt-1 text-[10px] text-zinc-600">
                                    平均每章 {genProgress.avgSectionTime}s
                                </div>
                            )}
                        </div>

                        {/* Two-panel layout */}
                        <div className="flex-1 flex overflow-hidden">
                            {/* Left: Section list */}
                            <div className="w-[280px] border-r border-zinc-800 overflow-y-auto bg-zinc-900/30">
                                {Object.entries(genProgress.sections).map(([title, info]) => (
                                    <div key={title}
                                        onClick={() => {
                                            if (info.status === 'done' || info.status === 'cached') {
                                                setViewingSection(viewingSection === title ? null : title);
                                            }
                                        }}
                                        className={`flex items-center py-2 px-3 text-[11px] border-b border-zinc-800/50 cursor-pointer transition-all ${info.status === 'generating'
                                            ? 'bg-orange-500/5 border-l-2 border-l-orange-500'
                                            : viewingSection === title
                                                ? 'bg-zinc-800 border-l-2 border-l-blue-500'
                                                : 'hover:bg-zinc-800/50 border-l-2 border-l-transparent'
                                            }`}>
                                        <span className="w-5 shrink-0 text-center">
                                            {info.status === 'pending' && <span className="text-zinc-600">○</span>}
                                            {info.status === 'generating' && <Loader2 size={12} className="text-orange-400 animate-spin" />}
                                            {info.status === 'done' && <CheckCircle size={12} className="text-emerald-400" />}
                                            {info.status === 'cached' && <span className="text-blue-400">⚡</span>}
                                            {info.status === 'error' && <AlertTriangle size={12} className="text-red-400" />}
                                        </span>
                                        <span className={`flex-1 ml-1.5 truncate ${info.status === 'generating' ? 'text-orange-200 font-bold' :
                                            info.status === 'done' || info.status === 'cached' ? 'text-zinc-300' :
                                                info.status === 'error' ? 'text-red-300' : 'text-zinc-600'
                                            }`}>
                                            {title}
                                        </span>
                                        {info.elapsed > 0 && (
                                            <span className="text-[9px] text-zinc-600 ml-1 shrink-0">{info.elapsed}s</span>
                                        )}
                                        {info.chars > 0 && (
                                            <span className="text-[9px] text-zinc-600 ml-1 shrink-0">{info.chars}字</span>
                                        )}
                                    </div>
                                ))}
                            </div>

                            {/* Right: Live content preview */}
                            <div className="flex-1 flex flex-col overflow-hidden bg-zinc-950">
                                {/* Content header */}
                                <div className="px-5 py-2.5 border-b border-zinc-800 bg-zinc-900/40 flex items-center justify-between shrink-0">
                                    <div className="flex items-center space-x-2">
                                        {(viewingSection || liveContent.title) && (
                                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-orange-500/10 text-orange-400 border border-orange-500/20">
                                                {viewingSection ? '📖 回顾' : '✍️ 生成中'}
                                            </span>
                                        )}
                                        <h3 className="text-[13px] font-bold text-zinc-200 truncate">
                                            {viewingSection || liveContent.title || '等待生成...'}
                                        </h3>
                                    </div>
                                    {viewingSection && (
                                        <button onClick={() => setViewingSection(null)}
                                            className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors px-2 py-1 rounded hover:bg-zinc-800">
                                            ← 返回实时
                                        </button>
                                    )}
                                </div>
                                {/* Content body */}
                                <div className="flex-1 overflow-y-auto px-5 py-4">
                                    <div className="text-[13px] text-zinc-300 leading-relaxed whitespace-pre-wrap font-[system-ui]">
                                        {viewingSection
                                            ? (completedSections[viewingSection] || '内容加载中...')
                                            : (liveContent.text || (
                                                <div className="text-zinc-600 text-center py-20">
                                                    <Loader2 size={24} className="animate-spin mx-auto mb-3 text-zinc-700" />
                                                    <p>等待章节开始生成...</p>
                                                </div>
                                            ))
                                        }
                                        {!viewingSection && liveContent.text && (
                                            <span className="inline-block w-2 h-4 bg-orange-400 animate-pulse ml-0.5 align-text-bottom" />
                                        )}
                                        <div ref={contentEndRef} />
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                ) : phase === 'done' ? (
                    /* ══════════════════════════════════════════════════════════ */
                    /* ── STEP 4: Completion Page with Preview + Regen ─────── */
                    /* ══════════════════════════════════════════════════════════ */
                    <div className="flex-1 flex overflow-hidden">
                        {/* Left: Full Document Preview */}
                        <div className="flex-1 overflow-y-auto p-6 bg-zinc-800/30">
                            <div className="max-w-[600px] mx-auto bg-white rounded shadow-2xl shadow-black/40 text-black"
                                style={{ aspectRatio: 'auto', minHeight: '800px' }}>
                                {/* Cover page simulation */}
                                <div className="px-12 pt-20 pb-10 border-b-2 border-gray-200">
                                    <p className="text-center text-gray-500 text-[11px] tracking-widest mb-8">投 标 文 件</p>
                                    <h1 className="text-center text-[20px] font-bold text-gray-900 leading-relaxed mb-4">
                                        {requirements?.bid_title || '投标文件'}
                                    </h1>
                                    <p className="text-center text-gray-500 text-[12px] mb-12">（商务技术部分）</p>
                                    <div className="w-48 mx-auto border-t border-gray-300 my-6"></div>
                                    <div className="text-center space-y-2 mt-8">
                                        <p className="text-gray-600 text-[12px]">投标人：{selectedCompany || requirements?.company_name || '投标人'}</p>
                                        <p className="text-gray-600 text-[12px]">日期：{new Date().toLocaleDateString('zh-CN')}</p>
                                    </div>
                                </div>

                                {/* Table of contents */}
                                <div className="px-12 py-8 border-b border-gray-100">
                                    <h2 className="text-center text-[14px] font-bold text-gray-800 tracking-[0.5em] mb-6">目    录</h2>
                                    <div className="space-y-1.5">
                                        {Object.entries(genProgress.sections)
                                            .filter(([, s]) => s.status === 'done' || s.status === 'cached')
                                            .map(([key], i) => (
                                                <div key={key} className="flex items-baseline text-[11px] cursor-pointer hover:bg-gray-50 px-2 py-0.5 -mx-2 rounded transition-colors"
                                                    onClick={() => {
                                                        const el = document.getElementById(`done-section-${i}`);
                                                        el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                                                    }}>
                                                    <span className="text-gray-800 font-medium shrink-0">
                                                        第{'一二三四五六七八九十'[i + 1] || (i + 2)}章
                                                    </span>
                                                    <span className="text-gray-700 ml-2 flex-1">{key}</span>
                                                    <span className="border-b border-dotted border-gray-300 flex-1 mx-2 min-w-[40px]"></span>
                                                    <span className="text-gray-400 text-[10px] shrink-0">{i + 3}</span>
                                                </div>
                                            ))
                                        }
                                    </div>
                                </div>

                                {/* Full content preview — using completedSections for complete text */}
                                <div className="px-12 py-6 space-y-8">
                                    {Object.entries(genProgress.sections)
                                        .filter(([, s]) => s.status === 'done' || s.status === 'cached')
                                        .map(([title], i) => {
                                            const content = completedSections[title] || '';
                                            const isLocked = lockedSections[title];
                                            const isRegen = regenerating === title;
                                            return (
                                                <div key={title} id={`done-section-${i}`} className="mb-6 scroll-mt-6">
                                                    <div className="flex items-center justify-between mb-3 pb-1 border-b border-gray-200">
                                                        <h3 className="text-[14px] font-bold text-gray-900">
                                                            第{'一二三四五六七八九十'[i + 1] || (i + 2)}章  {title}
                                                        </h3>
                                                        <div className="flex items-center gap-1.5">
                                                            {isLocked && (
                                                                <span className="text-[8px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-500 border border-blue-200">已锁定</span>
                                                            )}
                                                            {isRegen && (
                                                                <span className="text-[8px] px-1.5 py-0.5 rounded bg-orange-50 text-orange-500 border border-orange-200 flex items-center gap-1">
                                                                    <Loader2 size={8} className="animate-spin" /> 重新生成中
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                    <div className="text-[11px] text-gray-700 leading-relaxed whitespace-pre-wrap"
                                                        style={{ textIndent: '2em' }}>
                                                        {content || <span className="text-gray-400 italic">内容未生成</span>}
                                                    </div>
                                                </div>
                                            );
                                        })
                                    }
                                </div>
                            </div>
                        </div>

                        {/* Right: Stats & Actions with Regen/Lock */}
                        <div className="w-[300px] shrink-0 border-l border-zinc-800 flex flex-col overflow-hidden bg-zinc-900/80">
                            {/* Header */}
                            <div className="px-5 py-4 border-b border-zinc-800 flex flex-col items-center space-y-3">
                                <div className="w-14 h-14 bg-emerald-500/10 rounded-2xl flex items-center justify-center">
                                    <CheckCircle size={28} className="text-emerald-400" />
                                </div>
                                <div className="text-center">
                                    <h3 className="text-[15px] font-bold text-zinc-100">生成完成</h3>
                                    <p className="text-[11px] text-zinc-400 mt-1">
                                        {genProgress.done} 个章节 · {Object.values(genProgress.sections).reduce((s, x) => s + (x.chars || 0), 0).toLocaleString()} 字
                                    </p>
                                </div>
                                {/* Download */}
                                <button onClick={handleDownload}
                                    className="w-full flex items-center justify-center space-x-2 px-5 py-2.5 rounded-lg text-[12px] font-bold bg-emerald-500 text-white hover:bg-emerald-600 shadow-lg shadow-emerald-500/20 transition-all">
                                    <Download size={14} />
                                    <span>下载 Word 文件</span>
                                </button>
                            </div>

                            {/* Section list with lock/regen */}
                            <div className="flex-1 overflow-y-auto">
                                <div className="px-3 py-2">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wide">章节管理</span>
                                        <span className="text-[9px] text-zinc-600">
                                            {Object.values(lockedSections).filter(Boolean).length} 已锁定
                                        </span>
                                    </div>
                                    {Object.entries(genProgress.sections)
                                        .map(([title, info], idx) => {
                                            const isLocked = lockedSections[title];
                                            const isRegen = regenerating === title;
                                            const isExpanded = expandedDoneSection === title;
                                            const isDone = info.status === 'done' || info.status === 'cached';
                                            const isError = info.status === 'error';
                                            return (
                                                <div key={title} className={`rounded-lg mb-1 border transition-all ${
                                                    isRegen ? 'border-orange-500/30 bg-orange-500/5' :
                                                    isLocked ? 'border-blue-500/20 bg-blue-500/5' :
                                                    isExpanded ? 'border-zinc-600 bg-zinc-800/80' :
                                                    'border-zinc-800/50 hover:border-zinc-700 hover:bg-zinc-800/40'
                                                }`}>
                                                    <div className="flex items-center py-2 px-2.5 cursor-pointer"
                                                        onClick={() => setExpandedDoneSection(isExpanded ? null : title)}>
                                                        <span className="w-4 shrink-0 text-center text-[10px]">
                                                            {isError ? <AlertTriangle size={11} className="text-red-400" /> :
                                                             isRegen ? <Loader2 size={11} className="text-orange-400 animate-spin" /> :
                                                             isDone ? <CheckCircle size={11} className="text-emerald-400" /> :
                                                             <span className="text-zinc-600">○</span>}
                                                        </span>
                                                        <span className={`flex-1 ml-1.5 text-[11px] truncate ${
                                                            isError ? 'text-red-300' :
                                                            isRegen ? 'text-orange-200 font-bold' :
                                                            'text-zinc-300'
                                                        }`}>{title}</span>
                                                        <span className="text-[9px] text-zinc-600 shrink-0 ml-1">{info.chars || 0}字</span>
                                                        {isLocked && <Lock size={10} className="text-blue-400 ml-1 shrink-0" />}
                                                    </div>
                                                    {/* Expanded actions */}
                                                    {isExpanded && isDone && (
                                                        <div className="px-2.5 pb-2 flex items-center gap-1.5">
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    setLockedSections(prev => ({ ...prev, [title]: !prev[title] }));
                                                                }}
                                                                className={`flex items-center gap-1 text-[10px] px-2 py-1 rounded transition-all ${
                                                                    isLocked
                                                                        ? 'bg-blue-500/15 border border-blue-500/30 text-blue-300 hover:bg-blue-500/25'
                                                                        : 'bg-zinc-700/50 border border-zinc-600 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200'
                                                                }`}>
                                                                {isLocked ? <Lock size={10} /> : <Unlock size={10} />}
                                                                <span>{isLocked ? '解锁' : '锁定'}</span>
                                                            </button>
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    if (isLocked) { alert('该章节已锁定，请先解锁再重新生成'); return; }
                                                                    if (!confirm(`确认重新生成「${title}」？`)) return;
                                                                    regenerateSection(title);
                                                                }}
                                                                disabled={isLocked || isRegen}
                                                                className="flex items-center gap-1 text-[10px] px-2 py-1 rounded bg-orange-500/10 border border-orange-500/30 text-orange-300 hover:bg-orange-500/20 transition-all disabled:opacity-30 disabled:cursor-not-allowed">
                                                                <RefreshCw size={10} className={isRegen ? 'animate-spin' : ''} />
                                                                <span>{isRegen ? '生成中...' : '重新生成'}</span>
                                                            </button>
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    const el = document.getElementById(`done-section-${idx}`);
                                                                    el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                                                                }}
                                                                className="flex items-center gap-1 text-[10px] px-2 py-1 rounded bg-zinc-700/50 border border-zinc-600 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200 transition-all">
                                                                <Eye size={10} />
                                                                <span>查看</span>
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })
                                    }
                                </div>
                            </div>

                            {/* Footer */}
                            <div className="px-4 py-3 border-t border-zinc-800 flex items-center justify-center space-x-3">
                                <button onClick={() => setPhase('confirming')}
                                    className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors flex items-center gap-1">
                                    ← 返回大纲
                                </button>
                                <span className="text-zinc-800">|</span>
                                <button onClick={() => setShowMaterialPanel(true)}
                                    className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors flex items-center gap-1">
                                    <Package size={10} /> 素材库
                                </button>
                                <span className="text-zinc-800">|</span>
                                <button onClick={() => setShowStructure(true)}
                                    className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors">
                                    📋 大纲
                                </button>
                                <span className="text-zinc-800">|</span>
                                <button onClick={reset}
                                    className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors">
                                    🔄 新文件
                                </button>
                            </div>
                        </div>
                    </div>
                ) : (
                    /* ── Chat / Parsing Messages ── */
                    <>
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
                                                ) : null}
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
                        {/* Bottom hint during parsing */}
                        <div className="shrink-0 border-t border-zinc-800 bg-zinc-900/90 backdrop-blur px-4 py-3">
                            {/* Step progress indicator */}
                            {(() => {
                                const steps = [
                                    { label: '上传文件', icon: '📄' },
                                    { label: '文档解析', icon: '🔍' },
                                    { label: 'AI 深度分析', icon: '🤖' },
                                    { label: '构建索引', icon: '📊' },
                                ];
                                const currentStep = parseProgress.step || 0;
                                const elapsed = parseProgress.startTime ? Math.round((Date.now() - parseProgress.startTime) / 1000) : 0;
                                return (
                                    <div>
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center space-x-1">
                                                {steps.map((s, i) => (
                                                    <div key={i} className="flex items-center">
                                                        <div className={`flex items-center space-x-1 px-2 py-1 rounded-md text-[10px] font-medium transition-all duration-300 ${
                                                            i < currentStep ? 'bg-emerald-500/20 text-emerald-400' :
                                                            i === currentStep ? 'bg-orange-500/20 text-orange-300 animate-pulse' :
                                                            'bg-zinc-800 text-zinc-600'
                                                        }`}>
                                                            <span>{i < currentStep ? '✓' : s.icon}</span>
                                                            <span>{s.label}</span>
                                                        </div>
                                                        {i < steps.length - 1 && (
                                                            <div className={`w-4 h-px mx-0.5 ${i < currentStep ? 'bg-emerald-500/40' : 'bg-zinc-700'}`} />
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                            <span className="text-[10px] text-zinc-500">⏱ {elapsed}s</span>
                                        </div>
                                        <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
                                            <div className="h-full bg-gradient-to-r from-orange-500 to-amber-500 rounded-full transition-all duration-700"
                                                style={{ width: `${Math.min((currentStep / 3) * 100, 100)}%` }} />
                                        </div>
                                    </div>
                                );
                            })()}
                        </div>
                    </>
                )}
            </div >

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
            )
            }
        </>
    );
}
