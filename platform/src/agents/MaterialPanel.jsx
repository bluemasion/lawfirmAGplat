import { useState, useEffect, useCallback } from 'react';
import { X, Plus, Trash2, Edit3, Users, Briefcase, Award, ArrowLeft, Save, Loader2, ChevronDown, ChevronRight, FileText, File, ExternalLink, Upload, CheckCircle2, AlertCircle, RefreshCw, ImageIcon, Building2 } from 'lucide-react';

const API_BASE = `http://${window.location.hostname}:8001`;

const TABS = [
    { key: 'resumes', label: '人员简历', icon: Users, emoji: '👤' },
    { key: 'projects', label: '项目业绩', icon: Briefcase, emoji: '💼' },
    { key: 'qualifications', label: '资质证书', icon: Award, emoji: '🏅' },
];

const RESUME_FIELDS = [
    { key: 'name', label: '姓名', required: true },
    { key: 'title', label: '职位' },
    { key: 'years_of_practice', label: '执业年限' },
    { key: 'specialty', label: '专业方向' },
    { key: 'license_number', label: '执业证号' },
    { key: 'education', label: '学历' },
    { key: 'representative_cases', label: '代表案例', array: true },
    { key: 'brief_bio', label: '简介', multiline: true },
];

const PROJECT_FIELDS = [
    { key: 'project_name', label: '项目名称', required: true },
    { key: 'client', label: '委托方' },
    { key: 'project_type', label: '项目类型' },
    { key: 'contract_amount', label: '合同金额' },
    { key: 'period', label: '服务期间' },
    { key: 'lead_lawyer', label: '项目负责人' },
    { key: 'description', label: '项目描述', multiline: true },
];

const QUAL_FIELDS = [
    { key: 'name', label: '资质名称', required: true },
    { key: 'number', label: '编号' },
    { key: 'issuer', label: '颁发机构' },
    { key: 'valid_until', label: '有效期至' },
];

const FIELD_MAP = {
    resumes: RESUME_FIELDS,
    projects: PROJECT_FIELDS,
    qualifications: QUAL_FIELDS,
};

const KEY_FIELD = {
    resumes: 'name',
    projects: 'project_name',
    qualifications: 'name',
};

/* ── Source Files Block (shared across all card types) ── */
function SourceFilesBlock({ data }) {
    if (!data || (!data.loading && data.files.length === 0)) return null;

    const fileIcon = (type) => {
        const icons = { docx: '📄', doc: '📄', pdf: '📕', xlsx: '📊', xls: '📊', pptx: '📊', png: '🖼️', jpg: '🖼️', jpeg: '🖼️' };
        return icons[type] || '📎';
    };

    return (
        <div className="px-5 py-3 border-t border-zinc-700/50 bg-zinc-900/50">
            <div className="text-[10px] text-zinc-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <FileText size={10} />
                <span>关联原始文件</span>
                {data.loading && <Loader2 size={10} className="animate-spin text-orange-400" />}
            </div>
            <div className="space-y-1">
                {data.files.map((f, fi) => {
                    const previewUrl = `${API_BASE}/api/bidding/materials/preview?path=${encodeURIComponent(f.relative_path)}`;
                    return (
                        <a
                            key={fi}
                            href={previewUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center text-[12px] px-2 py-1.5 -mx-2 rounded-md hover:bg-zinc-700/40 cursor-pointer transition-colors group/file"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <span className="mr-2 text-sm">{fileIcon(f.file_type)}</span>
                            <span className="text-zinc-200 truncate flex-1 group-hover/file:text-orange-300 transition-colors">{f.filename}</span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-700/60 text-zinc-400 ml-2 shrink-0">{f.folder}</span>
                            <span className="text-[10px] text-zinc-500 ml-2 shrink-0">{f.size_display}</span>
                            <ExternalLink size={11} className="ml-2 text-zinc-600 group-hover/file:text-orange-400 transition-colors shrink-0" />
                        </a>
                    );
                })}
            </div>
        </div>
    );
}

/* ── Images Block (show extracted images from Word docs) ── */
function ImagesBlock({ images }) {
    const [lightbox, setLightbox] = useState(null);
    if (!images || images.length === 0) return null;

    return (
        <>
            <div className="px-5 py-3 border-t border-zinc-700/50 bg-zinc-900/50">
                <div className="text-[10px] text-zinc-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                    <ImageIcon size={10} />
                    <span>文档内嵌图片 ({images.length})</span>
                </div>
                <div className="flex flex-wrap gap-2">
                    {images.map((img, i) => {
                        const src = `${API_BASE}/api/bidding/materials/images/${img}`;
                        return (
                            <div
                                key={i}
                                className="w-20 h-20 rounded-lg border border-zinc-700 overflow-hidden cursor-pointer hover:border-orange-500/60 hover:shadow-lg hover:shadow-orange-500/10 transition-all group/img relative"
                                onClick={(e) => { e.stopPropagation(); setLightbox(src); }}
                            >
                                <img
                                    src={src}
                                    alt={img}
                                    className="w-full h-full object-cover group-hover/img:scale-110 transition-transform duration-200"
                                    onError={(e) => { e.target.style.display = 'none'; }}
                                />
                                <div className="absolute inset-0 bg-black/0 group-hover/img:bg-black/20 transition-colors flex items-center justify-center">
                                    <ExternalLink size={14} className="text-white opacity-0 group-hover/img:opacity-80 transition-opacity" />
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
            {/* Lightbox */}
            {lightbox && (
                <div
                    className="fixed inset-0 z-[9999] bg-black/80 flex items-center justify-center p-8 cursor-pointer"
                    onClick={() => setLightbox(null)}
                >
                    <img
                        src={lightbox}
                        alt="preview"
                        className="max-w-full max-h-full rounded-xl shadow-2xl border border-zinc-700"
                        onClick={(e) => e.stopPropagation()}
                    />
                    <button
                        className="absolute top-6 right-6 text-white/70 hover:text-white p-2 rounded-full bg-black/50 hover:bg-black/80 transition-colors"
                        onClick={() => setLightbox(null)}
                    >
                        <X size={20} />
                    </button>
                </div>
            )}
        </>
    );
}

export default function MaterialPanel({ onClose }) {
    const [activeTab, setActiveTab] = useState('resumes');
    const [materials, setMaterials] = useState({ resumes: [], projects: [], qualifications: [] });
    const [summary, setSummary] = useState({ resumes: 0, projects: 0, qualifications: 0, narrative_chunks: 0 });
    const [loading, setLoading] = useState(true);
    const [editingItem, setEditingItem] = useState(null); // { mode: 'edit'|'add', data: {} }
    const [saving, setSaving] = useState(false);
    const [expandedIdx, setExpandedIdx] = useState(null); // which item index is expanded
    const [sourceFiles, setSourceFiles] = useState({}); // { name: { loading, files: [] } }

    // ── Company state ──
    const [companies, setCompanies] = useState([]); // [{name, total, resumes, projects, qualifications}]
    const [selectedCompany, setSelectedCompany] = useState(''); // '' = all
    const [viewMode, setViewMode] = useState('companies'); // 'companies' | 'detail'
    const [addingCompany, setAddingCompany] = useState(false);
    const [newCompanyName, setNewCompanyName] = useState('');
    const [deletingCompany, setDeletingCompany] = useState(null); // company object to delete

    // ── Upload + Diff Review state ──
    const [uploading, setUploading] = useState(false);
    const [uploadStep, setUploadStep] = useState(0); // 0=idle, 1=uploading, 2=extracting, 3=comparing, 4=done
    const [uploadFileName, setUploadFileName] = useState('');
    const [diffReview, setDiffReview] = useState(null); // { upload_id, diff, extracted, selected }

    const UPLOAD_STEPS = [
        { label: '上传文件', icon: '📤', desc: '正在上传文件到服务器...' },
        { label: 'AI 智能提取', icon: '🤖', desc: '大语言模型正在识别简历、业绩、资质...' },
        { label: '变更对比', icon: '🔍', desc: '与现有素材库逐条对比差异...' },
        { label: '提取完成', icon: '✅', desc: '提取与对比已完成，请确认入库' },
    ];

    // ── File Upload Handler ──
    const handleFileUpload = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        e.target.value = ''; // reset input

        setUploading(true);
        setUploadFileName(file.name);
        setUploadStep(1); // uploading

        try {
            const formData = new FormData();
            formData.append('file', file);
            // Don't send company in upload — let AI detect from content first

            // Step 2: AI extraction (happens server-side)
            setTimeout(() => setUploadStep(2), 800);

            const res = await fetch(`${API_BASE}/api/bidding/upload-historical`, {
                method: 'POST',
                body: formData,
            });
            const result = await res.json();

            if (!result.success) {
                alert(`提取失败: ${result.message}`);
                setUploading(false);
                setUploadStep(0);
                return;
            }

            // Step 3: Comparing
            setUploadStep(3);

            const { upload_id, extracted } = result.data;
            const docType = result.data.doc_type || {};
            let diff = result.data.diff || {};

            console.log('[MaterialPanel] doc_type:', JSON.stringify(docType));
            console.log('[MaterialPanel] extracted:', JSON.stringify(extracted));

            // Handle tender file warning
            if (docType.doc_type === 'tender') {
                const proceed = confirm(
                    `⚠️ ${result.data.message || '检测到招标文件'}\n\n点击"确定"仍然尝试提取素材，点击"取消"返回。`
                );
                if (!proceed) {
                    setUploading(false);
                    setUploadStep(0);
                    return;
                }
            }

            // Fallback: if diff is empty but materials has items, build diff from materials
            const materials = result.data.materials || {};
            const hasDiffItems = Object.values(diff).some(arr => Array.isArray(arr) && arr.length > 0);
            const hasMaterials = ['resumes', 'projects', 'qualifications'].some(
                cat => Array.isArray(materials[cat]) && materials[cat].length > 0
            );

            if (!hasDiffItems && hasMaterials) {
                console.log('[MaterialPanel] diff empty but materials found, building synthetic diff');
                diff = {};
                for (const cat of ['resumes', 'projects', 'qualifications']) {
                    const items = materials[cat];
                    if (Array.isArray(items) && items.length > 0) {
                        diff[cat] = items.map(item => ({
                            action: 'new',
                            name: item.name || item.project_name || item.title || '未知',
                            data: item,
                        }));
                    }
                }
            }

            // Check if we have anything to show
            const totalItems = Object.values(diff).reduce(
                (sum, arr) => sum + (Array.isArray(arr) ? arr.length : 0), 0
            );
            if (totalItems === 0) {
                alert('⚠️ 未从文件中提取到可入库的素材（简历/业绩/资质）。\n可能原因：文件格式不支持、内容无法识别、或 AI 服务暂时不可用。');
                setUploading(false);
                setUploadStep(0);
                return;
            }

            // Build selection map
            const selected = {};
            for (const [category, items] of Object.entries(diff)) {
                if (!Array.isArray(items)) continue;
                selected[category] = {};
                for (let idx = 0; idx < items.length; idx++) {
                    const item = items[idx];
                    const key = item.name || item.project_name || item.title
                        || (item.data && (item.data.name || item.data.project_name))
                        || `idx:${idx}`;
                    selected[category][key] = item.action !== 'unchanged';
                }
            }

            // Step 4: Done
            await new Promise(r => setTimeout(r, 600));
            setUploadStep(4);
            await new Promise(r => setTimeout(r, 500));

            setDiffReview({
                upload_id, diff, extracted, selected,
                source_file: file.name, doc_type: docType,
                company: result.data.detected_company || result.data.company || selectedCompany || '',
                detected_company: result.data.detected_company || '',
            });
        } catch (err) {
            alert(`上传失败: ${err.message}`);
        } finally {
            setUploading(false);
            setUploadStep(0);
        }
    };

    // ── Confirm selected items ──
    const handleConfirmUpload = async () => {
        if (!diffReview) return;
        setUploading(true);

        try {
            // Build selected lists — resolve actual names from diff data
            const resolveNames = (category, keyField) => {
                const sel = diffReview.selected[category] || {};
                const diffItems = diffReview.diff[category] || [];
                const selectedKeys = Object.entries(sel).filter(([, v]) => v).map(([k]) => k);
                // Map keys back to actual names from diff items
                return selectedKeys.map(k => {
                    if (k.startsWith('idx:')) {
                        const idx = parseInt(k.slice(4), 10);
                        const item = diffItems[idx];
                        return item ? (item[keyField] || item.data?.[keyField] || k) : k;
                    }
                    return k;
                }).filter(Boolean);
            };
            const selectedResumes = resolveNames('resumes', 'name');
            const selectedProjects = resolveNames('projects', 'project_name');
            const selectedQuals = resolveNames('qualifications', 'name');

            const payload = {
                upload_id: diffReview.upload_id,
                company: diffReview.company || selectedCompany || '',
                selected_resumes: selectedResumes,
                selected_projects: selectedProjects,
                selected_qualifications: selectedQuals,
            };
            console.log('[MaterialPanel] Confirm payload:', JSON.stringify(payload));

            const res = await fetch(`${API_BASE}/api/bidding/confirm-materials`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const result = await res.json();
            console.log('[MaterialPanel] Confirm result:', JSON.stringify(result));
            if (result.success) {
                setDiffReview(null);
                // Navigate to the confirmed company
                const confirmedCompany = payload.company;
                if (confirmedCompany) {
                    setSelectedCompany(confirmedCompany);
                    setViewMode('detail');
                }
                loadMaterials();
                loadCompanies();
            } else {
                alert(`入库失败: ${result.message}`);
            }
        } catch (err) {
            console.error('[MaterialPanel] Confirm error:', err);
            alert(`入库失败: ${err.message}`);
        } finally {
            setUploading(false);
        }
    };

    // Toggle selection
    const toggleSelection = (category, key) => {
        setDiffReview(prev => ({
            ...prev,
            selected: {
                ...prev.selected,
                [category]: {
                    ...prev.selected[category],
                    [key]: !prev.selected[category][key],
                }
            }
        }));
    };

    // ── Load companies ──
    const loadCompanies = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/bidding/materials/companies`);
            const data = await res.json();
            if (data.success) {
                setCompanies(data.data.companies || []);
                // Auto-select default company on first load
                if (!selectedCompany && data.data.default) {
                    setSelectedCompany(data.data.default);
                }
            }
        } catch (e) {
            console.error('Failed to load companies:', e);
        }
    }, [selectedCompany]);

    // ── Load materials (company-filtered) ──
    const loadMaterials = useCallback(async () => {
        setLoading(true);
        try {
            const companyParam = selectedCompany ? `?company=${encodeURIComponent(selectedCompany)}` : '';
            const [matRes, sumRes] = await Promise.all([
                fetch(`${API_BASE}/api/bidding/materials${companyParam}`),
                fetch(`${API_BASE}/api/bidding/materials/summary${companyParam}`),
            ]);
            const matData = await matRes.json();
            const sumData = await sumRes.json();
            if (matData.success) setMaterials(matData.data);
            if (sumData.success) setSummary(sumData.data);
        } catch (e) {
            console.error('Failed to load materials:', e);
        } finally {
            setLoading(false);
        }
    }, [selectedCompany]);

    // Initial load
    useEffect(() => {
        loadCompanies();
    }, []);

    // Reload materials when company changes
    useEffect(() => {
        loadMaterials();
    }, [selectedCompany, loadMaterials]);

    // ── Delete ──
    const handleDelete = async (tab, item) => {
        const keyField = KEY_FIELD[tab];
        const name = item[keyField];
        if (!confirm(`确定删除 "${name}"？`)) return;

        const endpoint = tab === 'projects'
            ? `${API_BASE}/api/bidding/materials/projects/${encodeURIComponent(name)}`
            : tab === 'resumes'
                ? `${API_BASE}/api/bidding/materials/resumes/${encodeURIComponent(name)}`
                : `${API_BASE}/api/bidding/materials/qualifications/${encodeURIComponent(name)}`;

        try {
            const res = await fetch(endpoint, { method: 'DELETE' });
            const result = await res.json();
            if (result.success) {
                loadMaterials();
            }
        } catch (e) {
            console.error('Delete failed:', e);
        }
    };

    // ── Save (edit or add) ──
    const handleSave = async () => {
        if (!editingItem) return;
        setSaving(true);

        try {
            if (editingItem.mode === 'add') {
                const res = await fetch(`${API_BASE}/api/bidding/materials/add`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ type: activeTab, data: editingItem.data }),
                });
                await res.json();
            } else {
                const keyField = KEY_FIELD[activeTab];
                const name = editingItem.originalName || editingItem.data[keyField];
                const endpoint = activeTab === 'projects'
                    ? `${API_BASE}/api/bidding/materials/projects/${encodeURIComponent(name)}`
                    : activeTab === 'resumes'
                        ? `${API_BASE}/api/bidding/materials/resumes/${encodeURIComponent(name)}`
                        : `${API_BASE}/api/bidding/materials/qualifications/${encodeURIComponent(name)}`;

                const res = await fetch(endpoint, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ updates: editingItem.data }),
                });
                await res.json();
            }

            setEditingItem(null);
            loadMaterials();
        } catch (e) {
            console.error('Save failed:', e);
        } finally {
            setSaving(false);
        }
    };

    // ── Render item list ──
    const renderList = () => {
        const items = materials[activeTab] || [];
        const fields = FIELD_MAP[activeTab];
        const keyField = KEY_FIELD[activeTab];

        if (loading) {
            return (
                <div className="flex items-center justify-center py-16 text-zinc-500">
                    <Loader2 size={20} className="animate-spin mr-2" />
                    加载中...
                </div>
            );
        }

        if (!items.length) {
            return (
                <div className="text-center py-16 text-zinc-500 text-sm">
                    暂无数据，点击「+ 新增」添加
                </div>
            );
        }

        // Group items by source
        const grouped = {};
        items.forEach((item, idx) => {
            const src = item._source_section || '手动添加';
            if (!grouped[src]) grouped[src] = [];
            grouped[src].push({ item, idx });
        });
        const groupKeys = Object.keys(grouped);

        return (
            <div className="divide-y divide-zinc-800">
                {groupKeys.map((groupName) => {
                    const groupItems = grouped[groupName];
                    const imgCount = groupItems.reduce((sum, { item }) => sum + (item._images?.length || 0), 0);
                    return (
                        <div key={groupName}>
                            {/* Group header — only show if there are multiple groups */}
                            {groupKeys.length > 1 && (
                                <div className="px-4 py-2 bg-zinc-800/60 border-b border-zinc-700/40 flex items-center gap-2">
                                    <span className="text-[10px]">📁</span>
                                    <span className="text-[11px] font-medium text-zinc-400 truncate flex-1">{groupName}</span>
                                    <span className="text-[10px] text-zinc-600">{groupItems.length}项</span>
                                    {imgCount > 0 && (
                                        <span className="text-[10px] text-orange-400/70 flex items-center gap-0.5">
                                            🖼️ {imgCount}
                                        </span>
                                    )}
                                </div>
                            )}
                            {groupItems.map(({ item, idx }) => {
                                const isExpanded = expandedIdx === idx;
                                // Fetch source files when expanding
                                const lookupName = activeTab === 'resumes' ? item.name : activeTab === 'projects' ? item.project_name : item.name;
                                const handleExpand = () => {
                                    if (isExpanded) { setExpandedIdx(null); return; }
                                    setExpandedIdx(idx);
                                    if (lookupName && !sourceFiles[lookupName]) {
                                        setSourceFiles(prev => ({ ...prev, [lookupName]: { loading: true, files: [] } }));
                                        fetch(`${API_BASE}/api/bidding/materials/source-files/${encodeURIComponent(lookupName)}`)
                                            .then(r => r.json())
                                            .then(d => {
                                                if (d.success) {
                                                    setSourceFiles(prev => ({ ...prev, [lookupName]: { loading: false, files: d.data.files } }));
                                                }
                                            })
                                            .catch(() => setSourceFiles(prev => ({ ...prev, [lookupName]: { loading: false, files: [] } })));
                                    }
                                };
                                const currentSourceFiles = sourceFiles[lookupName] || { loading: false, files: [] };
                                return (
                                    <div key={idx} className="border-b border-zinc-800/50">
                                        {/* Clickable item row */}
                                        <div
                                            className={`flex items-center justify-between px-4 py-3 cursor-pointer transition-colors group ${isExpanded ? 'bg-zinc-800/70' : 'hover:bg-zinc-800/50'
                                                }`}
                                            onClick={handleExpand}
                                        >
                                            <div className="flex items-center space-x-2 flex-1 min-w-0">
                                                {isExpanded
                                                    ? <ChevronDown size={14} className="text-orange-400 shrink-0" />
                                                    : <ChevronRight size={14} className="text-zinc-600 shrink-0" />
                                                }
                                                <span className="text-[13px] font-semibold text-zinc-100">
                                                    {item[keyField] || '未命名'}
                                                </span>
                                                {activeTab === 'resumes' && item.title && (
                                                    <span className="text-[11px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                                                        {item.title}
                                                    </span>
                                                )}
                                                {activeTab === 'resumes' && item.specialty && (
                                                    <span className="text-[11px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                                        {item.specialty}
                                                    </span>
                                                )}
                                                {activeTab === 'resumes' && item.certifications?.map((cert, ci) => (
                                                    <span key={ci} className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/25">
                                                        🏅 {cert.replace(/ — .+$/, '')}
                                                    </span>
                                                ))}
                                                {activeTab === 'projects' && item.project_type && (
                                                    <span className="text-[11px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                                                        {item.project_type}
                                                    </span>
                                                )}
                                            </div>
                                            <div className="flex items-center space-x-1">
                                                <div className="text-[11px] text-zinc-500 mr-2 hidden sm:block">
                                                    {activeTab === 'resumes' && (
                                                        <>执业{item.years_of_practice || '?'}年{item.education ? ` · ${item.education}` : ''}</>
                                                    )}
                                                    {activeTab === 'projects' && (
                                                        <>{item.client || ''}{item.contract_amount ? ` · ${item.contract_amount}` : ''}</>
                                                    )}
                                                    {activeTab === 'qualifications' && (
                                                        <>
                                                            {item.cert_type === 'personal'
                                                                ? <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">👤 个人</span>
                                                                : <span className="text-[9px] px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30">🏢 企业</span>
                                                            }
                                                            {item.issuer || ''}{item.valid_until ? ` · 至${item.valid_until}` : ''}
                                                        </>
                                                    )}
                                                </div>
                                                <button onClick={(e) => { e.stopPropagation(); setEditingItem({ mode: 'edit', data: { ...item }, originalName: item[keyField] }); }}
                                                    className="p-1.5 rounded hover:bg-zinc-700 text-zinc-400 hover:text-blue-300 transition-colors opacity-0 group-hover:opacity-100"
                                                    title="编辑">
                                                    <Edit3 size={13} />
                                                </button>
                                                <button onClick={(e) => { e.stopPropagation(); handleDelete(activeTab, item); }}
                                                    className="p-1.5 rounded hover:bg-zinc-700 text-zinc-400 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
                                                    title="删除">
                                                    <Trash2 size={13} />
                                                </button>
                                            </div>
                                        </div>
                                        {/* ── Expanded detail card ── */}
                                        {isExpanded && (
                                            <div className="mx-4 mb-3 rounded-lg border border-zinc-700/80 bg-gradient-to-b from-zinc-800/90 to-zinc-900/90 overflow-hidden shadow-lg">

                                                {/* ━━ Resume Card ━━ */}
                                                {activeTab === 'resumes' && (
                                                    <div>
                                                        {/* Profile header */}
                                                        <div className="flex items-start px-5 py-4 border-b border-zinc-700/50">
                                                            <div className="w-14 h-14 rounded-full bg-gradient-to-br from-orange-500 to-amber-600 flex items-center justify-center text-white text-lg font-bold shrink-0 shadow-lg shadow-orange-500/20">
                                                                {(item.name || '?')[0]}
                                                            </div>
                                                            <div className="ml-4 flex-1 min-w-0">
                                                                <h3 className="text-[15px] font-bold text-zinc-100">{item.name || '未知'}</h3>
                                                                <div className="flex items-center flex-wrap gap-1.5 mt-1">
                                                                    {item.title && <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">{item.title}</span>}
                                                                    {item.specialty && <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">{item.specialty}</span>}
                                                                    {item.years_of_practice && <span className="text-[10px] px-2 py-0.5 rounded-full bg-zinc-700 text-zinc-300">执业{item.years_of_practice}年</span>}
                                                                </div>
                                                            </div>
                                                        </div>
                                                        {/* Info table */}
                                                        <table className="w-full text-[12px]">
                                                            <tbody>
                                                                {[
                                                                    ['执业证号', item.license_number],
                                                                    ['学历', item.education],
                                                                    ['专业方向', item.specialty],
                                                                    ['执业年限', item.years_of_practice ? `${item.years_of_practice}年` : null],
                                                                ].filter(([, v]) => v).map(([label, val], i) => (
                                                                    <tr key={i} className={i % 2 === 0 ? 'bg-zinc-800/30' : ''}>
                                                                        <td className="px-5 py-2 text-zinc-500 w-28 whitespace-nowrap">{label}</td>
                                                                        <td className="px-3 py-2 text-zinc-200">{val}</td>
                                                                    </tr>
                                                                ))}
                                                            </tbody>
                                                        </table>
                                                        {/* Brief bio */}
                                                        {item.brief_bio && (
                                                            <div className="px-5 py-3 border-t border-zinc-700/50">
                                                                <div className="text-[10px] text-zinc-500 uppercase tracking-wide mb-1">简介</div>
                                                                <p className="text-[12px] text-zinc-300 leading-relaxed">{item.brief_bio}</p>
                                                            </div>
                                                        )}
                                                        {/* Representative cases */}
                                                        {item.representative_cases?.length > 0 && (
                                                            <div className="px-5 py-3 border-t border-zinc-700/50">
                                                                <div className="text-[10px] text-zinc-500 uppercase tracking-wide mb-1.5">代表案例</div>
                                                                <div className="space-y-1">
                                                                    {item.representative_cases.map((c, ci) => (
                                                                        <div key={ci} className="flex items-start text-[12px]">
                                                                            <span className="text-orange-400 mr-2 mt-0.5 shrink-0">▸</span>
                                                                            <span className="text-zinc-300">{typeof c === 'string' ? c : JSON.stringify(c)}</span>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        )}
                                                        {/* Certifications linked to this person */}
                                                        {item.certifications?.length > 0 && (
                                                            <div className="px-5 py-3 border-t border-zinc-700/50">
                                                                <div className="text-[10px] text-zinc-500 uppercase tracking-wide mb-1.5">持有证书</div>
                                                                <div className="flex flex-wrap gap-1.5">
                                                                    {item.certifications.map((cert, ci) => (
                                                                        <span key={ci} className="inline-flex items-center text-[10px] px-2 py-1 rounded-md bg-amber-500/10 text-amber-300 border border-amber-500/20">
                                                                            🏅 {cert.replace(/ — .+$/, '')}
                                                                        </span>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        )}
                                                        {/* Extracted images */}
                                                        <ImagesBlock images={item._images} />
                                                        {/* Source files */}
                                                        <SourceFilesBlock data={currentSourceFiles} />
                                                    </div>
                                                )}

                                                {/* ━━ Project Card ━━ */}
                                                {activeTab === 'projects' && (
                                                    <div>
                                                        <div className="px-5 py-3 border-b border-zinc-700/50 flex items-center space-x-2">
                                                            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center text-white text-sm shrink-0">💼</div>
                                                            <h3 className="text-[14px] font-bold text-zinc-100">{item.project_name || '未知项目'}</h3>
                                                            {item.project_type && <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">{item.project_type}</span>}
                                                        </div>
                                                        <table className="w-full text-[12px]">
                                                            <tbody>
                                                                {[
                                                                    ['委托方', item.client],
                                                                    ['项目类型', item.project_type],
                                                                    ['合同金额', item.contract_amount],
                                                                    ['服务期间', item.period],
                                                                    ['项目负责人', item.lead_lawyer],
                                                                ].filter(([, v]) => v).map(([label, val], i) => (
                                                                    <tr key={i} className={i % 2 === 0 ? 'bg-zinc-800/30' : ''}>
                                                                        <td className="px-5 py-2 text-zinc-500 w-28 whitespace-nowrap">{label}</td>
                                                                        <td className="px-3 py-2 text-zinc-200">{val}</td>
                                                                    </tr>
                                                                ))}
                                                            </tbody>
                                                        </table>
                                                        {item.description && (
                                                            <div className="px-5 py-3 border-t border-zinc-700/50">
                                                                <div className="text-[10px] text-zinc-500 uppercase tracking-wide mb-1">项目描述</div>
                                                                <p className="text-[12px] text-zinc-300 leading-relaxed">{item.description}</p>
                                                            </div>
                                                        )}
                                                        {/* Extracted images */}
                                                        <ImagesBlock images={item._images} />
                                                        {/* Source files */}
                                                        <SourceFilesBlock data={currentSourceFiles} />
                                                    </div>
                                                )}

                                                {/* ━━ Qualification Card ━━ */}
                                                {activeTab === 'qualifications' && (
                                                    <div>
                                                        <div className="px-5 py-3 border-b border-zinc-700/50 flex items-center space-x-2">
                                                            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-yellow-600 flex items-center justify-center text-white text-sm shrink-0">🏅</div>
                                                            <h3 className="text-[14px] font-bold text-zinc-100">{item.name || '未知资质'}</h3>
                                                            {item.valid_until && (
                                                                <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-500/15 text-green-400 border border-green-500/30">
                                                                    有效至 {item.valid_until}
                                                                </span>
                                                            )}
                                                        </div>
                                                        <table className="w-full text-[12px]">
                                                            <tbody>
                                                                {[
                                                                    ['资质编号', item.number],
                                                                    ['颁发机构', item.issuer],
                                                                    ['有效期至', item.valid_until],
                                                                    ['来源章节', item._source_section],
                                                                ].filter(([, v]) => v).map(([label, val], i) => (
                                                                    <tr key={i} className={i % 2 === 0 ? 'bg-zinc-800/30' : ''}>
                                                                        <td className="px-5 py-2 text-zinc-500 w-28 whitespace-nowrap">{label}</td>
                                                                        <td className="px-3 py-2 text-zinc-200">{val}</td>
                                                                    </tr>
                                                                ))}
                                                            </tbody>
                                                        </table>
                                                        {/* Extracted images */}
                                                        <ImagesBlock images={item._images} />
                                                        {/* Source files */}
                                                        <SourceFilesBlock data={currentSourceFiles} />
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    );
                })}
            </div>
        );
    };

    // ── Render edit/add form ──
    const renderForm = () => {
        if (!editingItem) return null;
        const fields = FIELD_MAP[activeTab];

        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
                <div className="bg-zinc-900 border border-zinc-700 rounded-xl w-[480px] max-h-[80vh] overflow-y-auto shadow-2xl">
                    <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-700">
                        <h3 className="text-sm font-bold text-zinc-100">
                            {editingItem.mode === 'add' ? '+ 新增' : '✏️ 编辑'} {TABS.find(t => t.key === activeTab)?.label}
                        </h3>
                        <button onClick={() => setEditingItem(null)} className="text-zinc-500 hover:text-zinc-300">
                            <X size={16} />
                        </button>
                    </div>
                    <div className="px-5 py-4 space-y-3">
                        {fields.map(f => (
                            <div key={f.key}>
                                <label className="block text-[11px] text-zinc-400 mb-1">
                                    {f.label} {f.required && <span className="text-orange-400">*</span>}
                                </label>
                                {f.multiline ? (
                                    <textarea
                                        value={editingItem.data[f.key] || ''}
                                        onChange={(e) => setEditingItem(prev => ({
                                            ...prev, data: { ...prev.data, [f.key]: e.target.value }
                                        }))}
                                        rows={3}
                                        className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-[12px] text-zinc-100 focus:border-orange-500/60 focus:outline-none transition-colors resize-none"
                                    />
                                ) : (
                                    <input
                                        type="text"
                                        value={editingItem.data[f.key] || ''}
                                        onChange={(e) => setEditingItem(prev => ({
                                            ...prev, data: { ...prev.data, [f.key]: e.target.value }
                                        }))}
                                        className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-[12px] text-zinc-100 focus:border-orange-500/60 focus:outline-none transition-colors"
                                    />
                                )}
                            </div>
                        ))}
                    </div>
                    <div className="flex items-center justify-end space-x-2 px-5 py-3 border-t border-zinc-700">
                        <button onClick={() => setEditingItem(null)}
                            className="px-4 py-2 rounded-md text-[11px] font-bold text-zinc-400 hover:text-zinc-200 transition-colors">
                            取消
                        </button>
                        <button onClick={handleSave} disabled={saving}
                            className="flex items-center space-x-1.5 px-4 py-2 rounded-md text-[11px] font-bold bg-orange-500/20 border border-orange-500/40 text-orange-300 hover:bg-orange-500/30 transition-all disabled:opacity-40">
                            {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
                            <span>{saving ? '保存中...' : '保存'}</span>
                        </button>
                    </div>
                </div>
            </div>
        );
    };

    // ── Progress Overlay ──
    const renderProgressOverlay = () => {
        if (uploadStep === 0) return null;
        return (
            <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
                <div className="bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl w-full max-w-md p-6">
                    <h3 className="text-[15px] font-bold text-zinc-100 mb-1">📤 处理素材文件</h3>
                    <p className="text-[11px] text-zinc-500 mb-5 truncate">{uploadFileName}</p>

                    {/* Progress bar */}
                    <div className="h-1.5 bg-zinc-800 rounded-full mb-5 overflow-hidden">
                        <div
                            className="h-full bg-gradient-to-r from-blue-500 to-orange-500 rounded-full transition-all duration-700 ease-out"
                            style={{ width: `${(uploadStep / 4) * 100}%` }}
                        />
                    </div>

                    {/* Steps */}
                    <div className="space-y-3">
                        {UPLOAD_STEPS.map((step, idx) => {
                            const stepNum = idx + 1;
                            const isActive = uploadStep === stepNum;
                            const isDone = uploadStep > stepNum;
                            const isPending = uploadStep < stepNum;
                            return (
                                <div key={idx}
                                    className={`flex items-center space-x-3 p-2.5 rounded-lg transition-all duration-300 ${isActive ? 'bg-blue-500/10 border border-blue-500/30' :
                                        isDone ? 'bg-green-500/5 border border-green-500/20' :
                                            'border border-transparent opacity-40'
                                        }`}>
                                    <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-sm">
                                        {isDone ? '✅' : isActive ? (
                                            <Loader2 size={16} className="animate-spin text-blue-400" />
                                        ) : (
                                            <span className="text-zinc-600">{step.icon}</span>
                                        )}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className={`text-[12px] font-bold ${isActive ? 'text-blue-300' :
                                            isDone ? 'text-green-400' :
                                                'text-zinc-600'
                                            }`}>{step.label}</div>
                                        <div className={`text-[10px] ${isActive ? 'text-zinc-400' : 'text-zinc-600'
                                            }`}>{step.desc}</div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        );
    };

    // ── Diff Review Modal ──
    const renderDiffReview = () => {
        if (!diffReview) return null;
        const { diff, selected, source_file, doc_type } = diffReview;
        const docTypeLabels = { tender: '📋 招标文件', bid_document: '📑 完整投标文件', material: '📄 素材文件', unknown: '📄 文件' };
        const docTypeLabel = docTypeLabels[doc_type?.doc_type] || '📄 文件';
        const allCategories = ['resumes', 'projects', 'qualifications'];
        const categoryLabels = { resumes: '律师简历', projects: '项目业绩', qualifications: '资质证书' };
        const actionConfig = {
            new: { emoji: '🆕', label: '新增', color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/30' },
            updated: { emoji: '🔄', label: '有变化', color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/30' },
            unchanged: { emoji: '✅', label: '无变化', color: 'text-zinc-500', bg: 'bg-zinc-800/50 border-zinc-700/30' },
        };

        // Count totals
        let totalNew = 0, totalUpdated = 0, totalUnchanged = 0, totalSelected = 0;
        for (const items of Object.values(diff || {})) {
            if (!Array.isArray(items)) continue;
            for (const item of items) {
                if (item.action === 'new') totalNew++;
                else if (item.action === 'updated') totalUpdated++;
                else totalUnchanged++;
            }
        }
        for (const cat of Object.values(selected || {})) {
            for (const v of Object.values(cat || {})) { if (v) totalSelected++; }
        }

        return (
            <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
                <div className="bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col">
                    {/* Header */}
                    <div className="px-5 py-4 border-b border-zinc-700 flex items-center justify-between">
                        <div>
                            <h3 className="text-[15px] font-bold text-zinc-100">📋 提取结果预览</h3>
                            <p className="text-[11px] text-zinc-500 mt-0.5">
                                <span className="inline-block px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-300 mr-1.5">{docTypeLabel}</span>
                                {source_file}
                            </p>
                        </div>
                        <div className="flex items-center space-x-3 text-[11px]">
                            {totalNew > 0 && <span className="text-green-400">🆕 {totalNew} 新增</span>}
                            {totalUpdated > 0 && <span className="text-amber-400">🔄 {totalUpdated} 有变化</span>}
                            {totalUnchanged > 0 && <span className="text-zinc-500">✅ {totalUnchanged} 无变化</span>}
                        </div>
                    </div>

                    {/* Company selector */}
                    <div className="px-5 py-3 border-b border-zinc-700/60 bg-zinc-850/50">
                        <div className="flex items-center gap-2">
                            <Building2 size={14} className="text-zinc-500 shrink-0" />
                            <span className="text-[11px] text-zinc-500 shrink-0">归属于:</span>
                            <input
                                value={diffReview.company || ''}
                                onChange={e => setDiffReview(prev => ({ ...prev, company: e.target.value }))}
                                className="flex-1 px-2.5 py-1 rounded-md bg-zinc-800 border border-zinc-600 text-[12px] text-zinc-200 focus:outline-none focus:border-orange-500 transition-colors"
                                placeholder="输入公司/律所名称..."
                            />
                            {companies.length > 0 && (
                                <select
                                    value={diffReview.company || ''}
                                    onChange={e => setDiffReview(prev => ({ ...prev, company: e.target.value }))}
                                    className="px-2 py-1 rounded-md bg-zinc-800 border border-zinc-600 text-[11px] text-zinc-400 cursor-pointer focus:outline-none"
                                >
                                    <option value="">选择已有 ▼</option>
                                    {companies.map(c => (
                                        <option key={c.name} value={c.name}>{c.name} ({c.total})</option>
                                    ))}
                                </select>
                            )}
                        </div>
                        {diffReview.detected_company && diffReview.detected_company !== diffReview.company && (
                            <div className="mt-1.5 flex items-center gap-1.5">
                                <span className="text-[10px] text-zinc-500">🤖 AI 识别:</span>
                                <button
                                    onClick={() => setDiffReview(prev => ({ ...prev, company: prev.detected_company }))}
                                    className="text-[10px] px-2 py-0.5 rounded bg-blue-500/15 border border-blue-500/30 text-blue-300 hover:bg-blue-500/25 transition-all"
                                >
                                    使用 "{diffReview.detected_company}"
                                </button>
                            </div>
                        )}
                    </div>

                    {/* Body */}
                    <div className="flex-1 overflow-y-auto px-5 py-3 space-y-4">
                        {allCategories.map(cat => {
                            const items = diff[cat];
                            if (!items || items.length === 0) return null;
                            return (
                                <div key={cat}>
                                    <div className="text-[11px] font-bold text-zinc-400 uppercase tracking-wide mb-2">
                                        {categoryLabels[cat]} ({items.length})
                                    </div>
                                    <div className="space-y-2">
                                        {items.map((item, idx) => {
                                            const cfg = actionConfig[item.action] || actionConfig.unchanged;
                                            const key = item.name || item.project_name || item.title || `${cat}_${idx}`;
                                            const isSelected = selected[cat]?.[key] ?? false;
                                            return (
                                                <div key={idx}
                                                    className={`border rounded-lg p-3 transition-all ${cfg.bg} ${isSelected ? 'ring-1 ring-orange-500/40' : 'opacity-60'}`}>
                                                    <div className="flex items-center justify-between">
                                                        <div className="flex items-center space-x-2">
                                                            <input
                                                                type="checkbox"
                                                                checked={isSelected}
                                                                onChange={() => toggleSelection(cat, key)}
                                                                className="w-3.5 h-3.5 rounded accent-orange-500"
                                                            />
                                                            <span className="text-sm">{cfg.emoji}</span>
                                                            <span className="text-[13px] font-bold text-zinc-100">{key}</span>
                                                            <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${cfg.bg} ${cfg.color}`}>
                                                                {cfg.label}
                                                            </span>
                                                        </div>
                                                    </div>
                                                    {item.action === 'updated' && item.changes && (
                                                        <div className="mt-2 pl-7 space-y-1">
                                                            {Object.entries(item.changes || {}).map(([field, vals]) => {
                                                                const oldVal = Array.isArray(vals) ? vals[0] : null;
                                                                const newVal = Array.isArray(vals) ? vals[1] : String(vals);
                                                                return (
                                                                    <div key={field} className="flex items-center text-[11px]">
                                                                        <span className="text-zinc-500 w-20 shrink-0">{field}</span>
                                                                        {oldVal && (
                                                                            <>
                                                                                <span className="text-red-400/70 line-through mr-1">{oldVal}</span>
                                                                                <span className="text-zinc-600 mr-1">→</span>
                                                                            </>
                                                                        )}
                                                                        <span className="text-green-400">{newVal}</span>
                                                                    </div>
                                                                );
                                                            })}
                                                        </div>
                                                    )}
                                                    {/* Preview for new items */}
                                                    {item.action === 'new' && item.data && (
                                                        <div className="mt-2 pl-7 text-[11px] text-zinc-400">
                                                            {Object.entries(item.data || {})
                                                                .filter(([k, v]) => v && !k.startsWith('_') && k !== 'representative_cases')
                                                                .slice(0, 4)
                                                                .map(([k, v]) => (
                                                                    <span key={k} className="inline-block mr-3">
                                                                        <span className="text-zinc-600">{k}: </span>
                                                                        <span>{typeof v === 'string' ? v.slice(0, 30) : JSON.stringify(v).slice(0, 30)}</span>
                                                                    </span>
                                                                ))}
                                                        </div>
                                                    )}
                                                    {/* Image thumbnails from extracted data */}
                                                    {item.data?._images?.length > 0 && (
                                                        <div className="mt-2 pl-7 flex flex-wrap gap-1.5">
                                                            {item.data._images.map((img, ii) => (
                                                                <img
                                                                    key={ii}
                                                                    src={`${API_BASE}/api/bidding/materials/images/${img}`}
                                                                    alt={img}
                                                                    className="w-14 h-14 rounded border border-zinc-700 object-cover hover:border-orange-500/60 transition-colors"
                                                                    onError={(e) => { e.target.style.display = 'none'; }}
                                                                />
                                                            ))}
                                                            <span className="text-[10px] text-zinc-500 self-end ml-1">
                                                                🖼️ {item.data._images.length}张图片
                                                            </span>
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {/* Footer */}
                    <div className="px-5 py-3 border-t border-zinc-700 flex items-center justify-between">
                        <span className="text-[11px] text-zinc-500">
                            已选择 <span className="text-orange-300 font-bold">{totalSelected}</span> 项入库
                        </span>
                        <div className="flex items-center space-x-2">
                            <button
                                onClick={() => setDiffReview(null)}
                                className="px-4 py-2 rounded-md text-[11px] font-bold text-zinc-400 hover:text-zinc-200 transition-colors">
                                取消
                            </button>
                            <button
                                onClick={handleConfirmUpload}
                                disabled={uploading || totalSelected === 0}
                                className="flex items-center space-x-1.5 px-4 py-2 rounded-md text-[11px] font-bold bg-green-500/20 border border-green-500/40 text-green-300 hover:bg-green-500/30 transition-all disabled:opacity-40">
                                {uploading
                                    ? <><Loader2 size={12} className="animate-spin" /><span>入库中...</span></>
                                    : <><CheckCircle2 size={12} /><span>确认入库 ({totalSelected})</span></>
                                }
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    // ── Enter company detail ──
    const enterCompanyDetail = (companyName) => {
        setSelectedCompany(companyName);
        setViewMode('detail');
        setExpandedIdx(null);
    };

    // ── Render company list page ──
    const renderCompanyList = () => (
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {/* Company cards */}
            {companies.map(c => (
                <div
                    key={c.name}
                    onClick={() => enterCompanyDetail(c.name)}
                    className="rounded-xl border border-zinc-700/50 bg-gradient-to-r from-zinc-800/80 to-zinc-900/80 p-4 cursor-pointer hover:border-orange-500/40 hover:shadow-lg hover:shadow-orange-500/5 transition-all group"
                >
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-amber-600 flex items-center justify-center text-white text-lg font-bold shadow-lg shadow-orange-500/20">
                                {(c.name || '?')[0]}
                            </div>
                            <div>
                                <h3 className="text-[14px] font-bold text-zinc-100 group-hover:text-orange-300 transition-colors">{c.name}</h3>
                                <div className="flex items-center gap-2 mt-0.5">
                                    <span className="text-[11px] text-zinc-500">{c.total} 条素材</span>
                                </div>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            {c.resumes > 0 && (
                                <span className="text-[10px] px-2 py-1 rounded-md bg-blue-500/10 text-blue-300 border border-blue-500/20">
                                    👤 {c.resumes}人
                                </span>
                            )}
                            {c.projects > 0 && (
                                <span className="text-[10px] px-2 py-1 rounded-md bg-purple-500/10 text-purple-300 border border-purple-500/20">
                                    💼 {c.projects}项目
                                </span>
                            )}
                            {c.qualifications > 0 && (
                                <span className="text-[10px] px-2 py-1 rounded-md bg-amber-500/10 text-amber-300 border border-amber-500/20">
                                    🏅 {c.qualifications}资质
                                </span>
                            )}
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setDeletingCompany(c);
                                }}
                                className="p-1.5 rounded-md text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition-all opacity-0 group-hover:opacity-100"
                                title={`删除 ${c.name}`}
                            >
                                <Trash2 size={14} />
                            </button>
                            <ChevronRight size={16} className="text-zinc-600 group-hover:text-orange-400 transition-colors" />
                        </div>
                    </div>
                </div>
            ))}

            {/* Add new company */}
            {addingCompany ? (
                <div className="rounded-xl border border-dashed border-zinc-600 p-4">
                    <div className="flex items-center gap-2">
                        <Building2 size={16} className="text-zinc-500" />
                        <input
                            autoFocus
                            value={newCompanyName}
                            onChange={e => setNewCompanyName(e.target.value)}
                            onKeyDown={e => {
                                if (e.key === 'Enter' && newCompanyName.trim()) {
                                    fetch(`${API_BASE}/api/bidding/materials/default-company`, {
                                        method: 'PUT',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ company: newCompanyName.trim() }),
                                    }).then(() => {
                                        enterCompanyDetail(newCompanyName.trim());
                                        loadCompanies();
                                        setAddingCompany(false);
                                        setNewCompanyName('');
                                    });
                                }
                                if (e.key === 'Escape') {
                                    setAddingCompany(false);
                                    setNewCompanyName('');
                                }
                            }}
                            placeholder="输入公司/律所名称，按 Enter 确认"
                            className="flex-1 px-3 py-1.5 rounded-md bg-zinc-800 border border-zinc-600 text-[13px] text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:border-orange-500"
                        />
                        <button onClick={() => { setAddingCompany(false); setNewCompanyName(''); }}
                            className="text-zinc-500 hover:text-zinc-300 p-1">
                            <X size={14} />
                        </button>
                    </div>
                </div>
            ) : (
                <button
                    onClick={() => setAddingCompany(true)}
                    className="w-full rounded-xl border border-dashed border-zinc-700 p-3 text-[12px] text-zinc-500 hover:text-zinc-300 hover:border-zinc-500 transition-all flex items-center justify-center gap-1.5"
                >
                    <Plus size={14} />
                    <span>新增公司/律所</span>
                </button>
            )}

            {/* Empty state */}
            {companies.length === 0 && !loading && (
                <div className="text-center py-16">
                    <Building2 size={40} className="mx-auto text-zinc-700 mb-3" />
                    <p className="text-[13px] text-zinc-500">尚未添加任何公司</p>
                    <p className="text-[11px] text-zinc-600 mt-1">上传素材文件或手动新增公司开始使用</p>
                </div>
            )}

            {/* Delete confirmation modal */}
            {deletingCompany && (
                <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={() => setDeletingCompany(null)}>
                    <div className="bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl w-full max-w-sm p-5" onClick={e => e.stopPropagation()}>
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-10 h-10 rounded-lg bg-red-500/20 flex items-center justify-center">
                                <Trash2 size={20} className="text-red-400" />
                            </div>
                            <div>
                                <h3 className="text-[14px] font-bold text-zinc-100">删除确认</h3>
                                <p className="text-[11px] text-zinc-500">此操作不可恢复</p>
                            </div>
                        </div>
                        <p className="text-[13px] text-zinc-300 mb-1">
                            确定删除 <span className="font-bold text-zinc-100">「{deletingCompany.name}」</span> ？
                        </p>
                        <p className="text-[11px] text-zinc-500 mb-5">
                            将同时删除该公司下的 {deletingCompany.total} 条素材（{deletingCompany.resumes}简历 / {deletingCompany.projects}业绩 / {deletingCompany.qualifications}资质）
                        </p>
                        <div className="flex items-center justify-end gap-2">
                            <button
                                onClick={() => setDeletingCompany(null)}
                                className="px-4 py-1.5 rounded-lg text-[12px] text-zinc-400 bg-zinc-800 border border-zinc-700 hover:bg-zinc-700 transition-all"
                            >取消</button>
                            <button
                                onClick={() => {
                                    fetch(`${API_BASE}/api/bidding/materials/company/${encodeURIComponent(deletingCompany.name)}`, { method: 'DELETE' })
                                        .then(r => r.json())
                                        .then(() => {
                                            setDeletingCompany(null);
                                            loadCompanies();
                                        });
                                }}
                                className="px-4 py-1.5 rounded-lg text-[12px] font-bold text-white bg-red-600 hover:bg-red-500 transition-all"
                            >确认删除</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
                <div className="flex items-center space-x-3">
                    {viewMode === 'companies' ? (
                        /* Company list header */
                        <>
                            <button onClick={onClose}
                                className="flex items-center space-x-1 text-[11px] text-zinc-400 hover:text-zinc-200 transition-colors">
                                <ArrowLeft size={14} />
                                <span>返回</span>
                            </button>
                            <h2 className="text-sm font-bold text-zinc-100">📦 素材库</h2>
                            <span className="text-[10px] text-zinc-500">{companies.length} 家公司</span>
                        </>
                    ) : (
                        /* Company detail header — breadcrumb style */
                        <>
                            <button onClick={() => setViewMode('companies')}
                                className="flex items-center space-x-1 text-[11px] text-zinc-400 hover:text-zinc-200 transition-colors">
                                <ArrowLeft size={14} />
                                <span>素材库</span>
                            </button>
                            <span className="text-zinc-600">/</span>
                            <h2 className="text-sm font-bold text-zinc-100">{selectedCompany}</h2>
                            <div className="flex items-center space-x-2 text-[10px] text-zinc-500">
                                <span>{summary.resumes}人</span>
                                <span>·</span>
                                <span>{summary.projects}项目</span>
                                <span>·</span>
                                <span>{summary.qualifications}资质</span>
                            </div>
                        </>
                    )}
                </div>
                <div className="flex items-center space-x-2">
                    {/* Upload button */}
                    <input
                        type="file"
                        id="material-upload-input"
                        accept=".docx,.doc,.pdf"
                        className="hidden"
                        onChange={handleFileUpload}
                    />
                    <button
                        onClick={() => document.getElementById('material-upload-input').click()}
                        disabled={uploading}
                        className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-[11px] font-bold bg-blue-500/15 border border-blue-500/30 text-blue-300 hover:bg-blue-500/25 transition-all disabled:opacity-40">
                        {uploading
                            ? <><Loader2 size={12} className="animate-spin" /><span>处理中...</span></>
                            : <><Upload size={12} /><span>上传素材</span></>
                        }
                    </button>
                    {viewMode === 'detail' && (
                        <button onClick={() => setEditingItem({ mode: 'add', data: {} })}
                            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-[11px] font-bold bg-orange-500/20 border border-orange-500/40 text-orange-300 hover:bg-orange-500/30 transition-all">
                            <Plus size={12} />
                            <span>新增</span>
                        </button>
                    )}
                </div>
            </div>

            {viewMode === 'companies' ? (
                /* ── Level 1: Company List ── */
                renderCompanyList()
            ) : (
                /* ── Level 2: Company Detail ── */
                <>
                    {/* Tabs */}
                    <div className="flex border-b border-zinc-800">
                        {TABS.map(tab => {
                            const count = (materials[tab.key] || []).length;
                            return (
                                <button key={tab.key}
                                    onClick={() => setActiveTab(tab.key)}
                                    className={`flex items-center space-x-1.5 px-4 py-2.5 text-[12px] font-medium border-b-2 transition-all ${activeTab === tab.key
                                        ? 'border-orange-500 text-orange-300'
                                        : 'border-transparent text-zinc-500 hover:text-zinc-300'
                                        }`}>
                                    <span>{tab.emoji}</span>
                                    <span>{tab.label}</span>
                                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${activeTab === tab.key ? 'bg-orange-500/20 text-orange-300' : 'bg-zinc-800 text-zinc-500'
                                        }`}>{count}</span>
                                </button>
                            );
                        })}
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto">
                        {renderList()}
                    </div>
                </>
            )}

            {/* Edit/Add Form Modal */}
            {renderForm()}

            {/* Progress Overlay */}
            {renderProgressOverlay()}

            {/* Diff Review Modal */}
            {renderDiffReview()}
        </div>
    );
}
