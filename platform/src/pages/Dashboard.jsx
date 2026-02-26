import { useState, useEffect } from 'react';
import { LayoutDashboard, ShieldCheck, Database } from 'lucide-react';
import MetricCard from '../components/MetricCard';
import { getDashboardMetrics, getUtilizationData } from '../api/services';

export default function Dashboard() {
    const [metrics, setMetrics] = useState([]);
    const [utilization, setUtilization] = useState([]);

    useEffect(() => {
        getDashboardMetrics().then(setMetrics);
        getUtilizationData().then(setUtilization);
    }, []);

    return (
        <div className="p-6 space-y-8 animate-in">
            <div className="flex items-center justify-between border-b border-zinc-200 pb-4">
                <div className="flex items-center space-x-3">
                    <LayoutDashboard className="text-blue-600" size={24} />
                    <h1 className="text-lg font-bold text-zinc-800 tracking-tight uppercase">控制台概览 / Console Dashboard</h1>
                </div>
                <div className="px-3 py-1.5 bg-zinc-50 border border-zinc-300 rounded-sm text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Region: Asia-South-01 (SZ)</div>
            </div>

            <div className="grid grid-cols-4 gap-4">
                {metrics.map((m, i) => <MetricCard key={i} {...m} />)}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div className="lg:col-span-8 bg-white border border-zinc-200 rounded-sm shadow-sm overflow-hidden flex flex-col min-h-[350px]">
                    <div className="px-4 py-3 bg-[#f8f9fa] border-b border-zinc-200 flex justify-between items-center font-bold text-zinc-500 text-[10px] uppercase tracking-widest shadow-inner">
                        <span>实时算力负载监控 (Resource Utilization)</span>
                        <span className="text-emerald-600 flex items-center animate-pulse">
                            <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full mr-1"></div> 链路监控已激活
                        </span>
                    </div>
                    <div className="flex-1 p-10 h-full flex items-end space-x-2 bg-white">
                        {utilization.map((h, i) => (
                            <div key={i} className="flex-1 bg-blue-100 hover:bg-blue-600 transition-all rounded-t-sm group relative cursor-pointer" style={{ height: `${h}%` }}>
                                <div className="absolute -top-6 left-1/2 -translate-x-1/2 bg-zinc-900 text-white text-[9px] px-1 rounded opacity-0 group-hover:opacity-100 transition whitespace-nowrap font-bold z-20">
                                    {h}% Load
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="lg:col-span-4">
                    <div className="bg-[#151921] rounded-sm p-6 text-white shadow-2xl relative overflow-hidden border border-zinc-800 h-full flex flex-col justify-between">
                        <div className="relative z-10 space-y-4">
                            <h3 className="text-sm font-bold flex items-center border-b border-zinc-800 pb-4 uppercase tracking-tighter">
                                <ShieldCheck size={18} className="text-emerald-500 mr-2" /> Security Compliance
                            </h3>
                            <p className="text-[11px] text-zinc-400 leading-relaxed font-bold italic">
                                当前所有 AI 推理请求强制经过本地私有化 NER 脱敏网关。VPC-L5 加密链路已连接成功。
                            </p>
                        </div>
                        <div className="relative z-10 pt-8 border-t border-zinc-800">
                            <div className="flex justify-between text-[9px] uppercase font-bold text-zinc-500 tracking-widest mb-1">
                                <span>Security Level</span><span className="text-emerald-400 font-mono">L5 - Highest</span>
                            </div>
                            <div className="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden mt-1 shadow-inner">
                                <div className="bg-emerald-500 h-full w-full shadow-[0_0_8px_rgba(16,185,129,0.5)] animate-pulse"></div>
                            </div>
                        </div>
                        <Database size={160} className="absolute -right-16 -bottom-16 text-white/5 rotate-12 pointer-events-none" />
                    </div>
                </div>
            </div>
        </div>
    );
}
