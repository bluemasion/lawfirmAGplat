import { MoreHorizontal } from 'lucide-react';

export default function MetricCard({ label, value, trend, unit }) {
    return (
        <div className="bg-white border border-zinc-200 p-4 rounded-sm shadow-sm hover:shadow-md transition-all group">
            <div className="flex justify-between items-start mb-2">
                <span className="text-zinc-500 text-[10px] font-bold uppercase tracking-widest">{label}</span>
                <MoreHorizontal size={14} className="text-zinc-400 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer" />
            </div>
            <div className="flex items-baseline space-x-1">
                <span className="text-2xl font-bold text-zinc-900 tracking-tight">{value}</span>
                {unit && <span className="text-xs text-zinc-400 font-bold">{unit}</span>}
            </div>
            {trend && (
                <div className="mt-2 flex items-center text-[10px] font-bold">
                    <span className={trend.startsWith('+') ? 'text-emerald-600' : 'text-rose-600'}>{trend}</span>
                    <span className="text-zinc-400 ml-1 font-medium text-[9px]">较昨日</span>
                </div>
            )}
        </div>
    );
}
