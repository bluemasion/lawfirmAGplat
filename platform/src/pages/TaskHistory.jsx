import { useState, useEffect } from 'react';
import { FileText, Download, Clock, CheckCircle, Loader2, AlertTriangle, Trash2, RefreshCw, Building2, ChevronRight, Sparkles } from 'lucide-react';

const API_BASE = 'http://localhost:8001';

const STATUS_CONFIG = {
    done: { label: '已完成', color: 'text-emerald-600 bg-emerald-50 border-emerald-200', icon: CheckCircle },
    parsed: { label: '已解析', color: 'text-blue-600 bg-blue-50 border-blue-200', icon: Clock },
    generating: { label: '生成中', color: 'text-orange-600 bg-orange-50 border-orange-200', icon: Loader2 },
    error: { label: '失败', color: 'text-red-600 bg-red-50 border-red-200', icon: AlertTriangle },
};

function formatTime(ts) {
    if (!ts) return '—';
    const d = new Date(ts * 1000);
    const now = new Date();
    const diff = (now - d) / 1000;

    const pad = (n) => String(n).padStart(2, '0');
    const timeStr = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
    const dateStr = `${d.getMonth() + 1}/${d.getDate()}`;

    if (diff < 60) return '刚刚';
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
    if (diff < 86400 && d.getDate() === now.getDate()) return `今天 ${timeStr}`;
    if (diff < 172800) return `昨天 ${timeStr}`;
    return `${dateStr} ${timeStr}`;
}

function formatDuration(startTs, endTs) {
    if (!startTs || !endTs) return '—';
    const secs = Math.round(endTs - startTs);
    if (secs < 60) return `${secs}秒`;
    if (secs < 3600) return `${Math.floor(secs / 60)}分${secs % 60}秒`;
    return `${Math.floor(secs / 3600)}时${Math.floor((secs % 3600) / 60)}分`;
}

export default function TaskHistory({ onOpenTask }) {
    const [tasks, setTasks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [deletingId, setDeletingId] = useState(null);

    const fetchTasks = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_BASE}/api/bidding/tasks`);
            const data = await res.json();
            if (data.success) {
                setTasks(data.data || []);
            } else {
                setError(data.message || '加载失败');
            }
        } catch (e) {
            setError('无法连接后端服务: ' + e.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchTasks(); }, []);

    const handleDownload = (taskId) => {
        const url = `${API_BASE}/api/bidding/download/${taskId}`;
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', '');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const handleClearCache = async (taskId) => {
        if (!confirm(`确定要清除任务 ${taskId} 的缓存吗？清除后重新生成将重新调用 LLM。`)) return;
        setDeletingId(taskId);
        try {
            await fetch(`${API_BASE}/api/bidding/clear-cache/${taskId}`, { method: 'DELETE' });
            fetchTasks();
        } catch (e) {
            console.error('Clear cache failed:', e);
        } finally {
            setDeletingId(null);
        }
    };

    const doneTasks = tasks.filter(t => t.status === 'done');
    const otherTasks = tasks.filter(t => t.status !== 'done');

    return (
        <div className="p-6 space-y-6 animate-in">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-zinc-200 pb-4">
                <div className="flex items-center space-x-3">
                    <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-orange-500 to-amber-600 flex items-center justify-center shadow-lg shadow-orange-500/20">
                        <FileText size={18} className="text-white" />
                    </div>
                    <div>
                        <h1 className="text-lg font-bold text-zinc-800 tracking-tight">投标任务管理</h1>
                        <p className="text-[11px] text-zinc-400 font-medium">历史任务 · 文档下载 · 缓存管理</p>
                    </div>
                </div>
                <div className="flex items-center space-x-3">
                    <div className="flex items-center space-x-4 text-[11px] text-zinc-500">
                        <span className="flex items-center space-x-1">
                            <CheckCircle size={12} className="text-emerald-500" />
                            <span>{doneTasks.length} 已完成</span>
                        </span>
                        <span className="flex items-center space-x-1">
                            <Clock size={12} className="text-blue-500" />
                            <span>{otherTasks.length} 进行中</span>
                        </span>
                    </div>
                    <button
                        onClick={fetchTasks}
                        disabled={loading}
                        className="flex items-center space-x-1.5 px-3 py-1.5 text-[11px] font-bold text-zinc-500 hover:text-zinc-700 bg-zinc-50 hover:bg-zinc-100 border border-zinc-200 rounded-md transition-all disabled:opacity-40"
                    >
                        <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
                        <span>刷新</span>
                    </button>
                </div>
            </div>

            {/* Error */}
            {error && (
                <div className="flex items-center space-x-2 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-[12px]">
                    <AlertTriangle size={14} />
                    <span>{error}</span>
                </div>
            )}

            {/* Loading */}
            {loading && !tasks.length && (
                <div className="flex items-center justify-center py-20">
                    <Loader2 size={24} className="animate-spin text-orange-400" />
                    <span className="ml-3 text-zinc-400 text-sm">加载任务列表...</span>
                </div>
            )}

            {/* Empty */}
            {!loading && !tasks.length && !error && (
                <div className="flex flex-col items-center justify-center py-20 text-zinc-400">
                    <FileText size={48} className="mb-4 text-zinc-300" />
                    <p className="text-sm font-medium">暂无投标任务</p>
                    <p className="text-[11px] mt-1">上传招标文件开始第一个任务</p>
                </div>
            )}

            {/* Task List */}
            {tasks.length > 0 && (
                <div className="space-y-3">
                    {tasks.map((task) => {
                        const statusConf = STATUS_CONFIG[task.status] || STATUS_CONFIG.error;
                        const StatusIcon = statusConf.icon;
                        const isAnimating = task.status === 'generating';

                        return (
                            <div
                                key={task.task_id}
                                className="group bg-white border border-zinc-200 rounded-lg hover:border-orange-300 hover:shadow-md transition-all duration-200 overflow-hidden"
                            >
                                <div className="flex items-center px-5 py-4">
                                    {/* Left: Status icon */}
                                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 mr-4 border ${statusConf.color}`}>
                                        <StatusIcon size={18} className={isAnimating ? 'animate-spin' : ''} />
                                    </div>

                                    {/* Middle: Info */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center space-x-2">
                                            <h3 className="text-[13px] font-bold text-zinc-800 truncate">
                                                {task.tender_filename || '未命名文件'}
                                            </h3>
                                            <span className={`text-[9px] px-2 py-0.5 rounded-full border font-bold ${statusConf.color}`}>
                                                {statusConf.label}
                                            </span>
                                        </div>
                                        <div className="flex items-center space-x-4 mt-1.5 text-[11px] text-zinc-400">
                                            {task.company_name && (
                                                <span className="flex items-center space-x-1">
                                                    <Building2 size={11} />
                                                    <span className="text-zinc-600 font-medium">{task.company_name}</span>
                                                </span>
                                            )}
                                            <span className="flex items-center space-x-1">
                                                <Clock size={11} />
                                                <span>{formatTime(task.created_at)}</span>
                                            </span>
                                            {task.section_count > 0 && (
                                                <span className="flex items-center space-x-1">
                                                    <FileText size={11} />
                                                    <span>{task.section_count} 章节</span>
                                                </span>
                                            )}
                                            {task.completed_at && task.created_at && (
                                                <span className="flex items-center space-x-1">
                                                    <Sparkles size={11} />
                                                    <span>用时 {formatDuration(task.created_at, task.completed_at)}</span>
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Right: Actions */}
                                    <div className="flex items-center space-x-2 shrink-0 ml-4 opacity-0 group-hover:opacity-100 transition-opacity">
                                        {task.has_output && (
                                            <button
                                                onClick={() => handleDownload(task.task_id)}
                                                className="flex items-center space-x-1 px-3 py-1.5 text-[11px] font-bold text-white bg-orange-500 hover:bg-orange-600 rounded-md shadow-sm shadow-orange-500/20 transition-all"
                                            >
                                                <Download size={12} />
                                                <span>下载 .docx</span>
                                            </button>
                                        )}
                                        <button
                                            onClick={() => handleClearCache(task.task_id)}
                                            disabled={deletingId === task.task_id}
                                            className="flex items-center space-x-1 px-2.5 py-1.5 text-[11px] font-medium text-zinc-400 hover:text-red-500 hover:bg-red-50 border border-zinc-200 hover:border-red-200 rounded-md transition-all disabled:opacity-40"
                                            title="清除缓存"
                                        >
                                            <Trash2 size={12} />
                                        </button>
                                    </div>

                                    {/* Always visible download for touch */}
                                    {task.has_output && (
                                        <button
                                            onClick={() => handleDownload(task.task_id)}
                                            className="group-hover:hidden flex items-center ml-4 text-orange-500 hover:text-orange-600"
                                            title="下载文档"
                                        >
                                            <Download size={16} />
                                        </button>
                                    )}
                                </div>

                                {/* Task ID bar */}
                                <div className="border-t border-zinc-100 px-5 py-1.5 bg-zinc-50/60 flex items-center justify-between">
                                    <span className="text-[10px] text-zinc-400 font-mono">{task.task_id}</span>
                                    {task.status === 'parsed' && onOpenTask && (
                                        <button
                                            onClick={() => onOpenTask(task.task_id)}
                                            className="flex items-center space-x-1 text-[10px] text-orange-500 hover:text-orange-600 font-bold transition-colors"
                                        >
                                            <span>继续生成</span>
                                            <ChevronRight size={12} />
                                        </button>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
