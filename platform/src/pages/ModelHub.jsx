import { useState, useEffect } from 'react';
import { UserPlus, Database, Settings } from 'lucide-react';
import { getModelInstances } from '../api/services';

export default function ModelHub({ onSelectTest }) {
    const [instances, setInstances] = useState([]);
    useEffect(() => { getModelInstances().then(setInstances); }, []);

    return (
        <div className="p-8 space-y-8 animate-in">
            <div className="flex justify-between items-end border-b border-zinc-200 pb-4">
                <div>
                    <h2 className="text-xl font-bold text-zinc-800 tracking-tight uppercase">算力实例管理 / Instance Hub</h2>
                    <p className="text-[10px] text-zinc-400 font-bold uppercase tracking-widest mt-1">Management of Dedicated Legal Inference Nodes</p>
                </div>
                <button className="px-4 py-2 bg-[#151921] text-white text-[11px] font-bold rounded-sm shadow-lg flex items-center space-x-2 uppercase hover:bg-black transition-all">
                    <UserPlus size={14} /><span>Register New Node</span>
                </button>
            </div>
            <div className="bg-white border border-zinc-300 rounded-sm overflow-hidden shadow-xl shadow-zinc-100/50">
                <table className="w-full text-left text-[11px]">
                    <thead className="bg-[#f2f3f3] border-b border-zinc-300 text-zinc-600 font-bold uppercase tracking-tighter">
                        <tr>
                            <th className="px-6 py-4">实例名称 / ID</th>
                            <th className="px-6 py-4">运行状态</th>
                            <th className="px-6 py-4">部署环境</th>
                            <th className="px-6 py-4 text-center">平均响应 (Latency)</th>
                            <th className="px-4 py-4 text-right">管理操作</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-200 font-bold text-zinc-700">
                        {instances.map((ins, i) => (
                            <tr key={i} className="hover:bg-blue-50/40 transition-colors group">
                                <td className="px-6 py-4 font-mono">
                                    <div className="flex items-center space-x-3">
                                        <div className={`w-2 h-2 rounded-full shadow-sm ${ins.status === 'Running' ? 'bg-emerald-500' : 'bg-blue-400 animate-pulse'}`}></div>
                                        <span className="text-zinc-900 font-bold tracking-tight">{ins.name}</span>
                                    </div>
                                </td>
                                <td className="px-6 py-4 italic text-[10px] text-zinc-400 uppercase tracking-widest">{ins.status}</td>
                                <td className="px-6 py-4 flex items-center text-zinc-500 font-medium italic"><Database size={12} className="mr-1.5 text-zinc-400" />{ins.provider}</td>
                                <td className="px-6 py-4 font-mono text-blue-600 text-center tracking-tighter">{ins.latency}</td>
                                <td className="px-4 py-4 text-right space-x-4">
                                    <button onClick={() => onSelectTest(ins)} className="text-blue-600 hover:text-blue-800 underline underline-offset-4 uppercase italic">Launch Console</button>
                                    <button className="text-zinc-300 group-hover:text-zinc-600 transition-colors"><Settings size={14} /></button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
