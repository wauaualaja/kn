import { useEffect, useState, useCallback } from "react";
import {
  Banknote, TrendingUp, ArrowUpRight, Receipt, AlertTriangle,
  Clock, PackageX, Award, RefreshCw, Trophy,
} from "lucide-react";
import axios, { API } from "../../services/apiClient";
import PeriodUnlockCard from "../../components/PeriodUnlockCard";
import ErrorNotice from "../../components/ErrorNotice";

const fmt = new Intl.NumberFormat("id-ID");
const fmtCur = (v) => `Rp ${fmt.format(Math.round(v || 0))}`;

function KPICard({ icon: Icon, label, value, sub, color = "#007AFF", loading }) {
  return (
    <div data-testid={`kpi-${label.toLowerCase().replace(/\s+/g, "-")}`}
      className="rounded-xl border border-[#EFF0F2] bg-white p-4 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <div className="rounded-lg p-1.5" style={{ background: `${color}18` }}>
          <Icon size={16} style={{ color }} />
        </div>
        <span className="text-[12px] font-semibold text-[#6B6B73]">{label}</span>
      </div>
      {loading ? (
        <div className="h-7 bg-[#F5F5F7] rounded animate-pulse" />
      ) : (
        <p className="text-2xl font-bold text-[#1C1C1E] tabular-nums">{value}</p>
      )}
      {sub && <p className="text-[11px] text-[#6B6B73]">{sub}</p>}
    </div>
  );
}

export default function AdminHome({ token, selectedEntity = "all", onNavigate }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);

  const headers = { Authorization: `Bearer ${token}` };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = selectedEntity && selectedEntity !== "all" ? { entity_id: selectedEntity } : {};
      const res = await axios.get(`${API}/home/admin`, { headers, params });
      setData(res.data);
      setError("");
    } catch (e) {
      setError(e.response?.data?.detail || "Gagal memuat Control Tower. Coba lagi.");
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, selectedEntity]);

  useEffect(() => { load(); }, [load]);

  const sales = data?.sales || {};
  const ar = data?.ar || {};
  const lowStock = data?.low_stock || {};
  const board = data?.leaderboard_top || [];
  const overdue = data?.top_overdue || [];

  return (
    <section data-testid="admin-home" className="section-card">
      <div className="section-head">
        <p className="text-[12px] text-[#6B6B73] min-w-0 truncate">Pantauan penjualan, piutang & stok — real-time</p>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button onClick={load} className="secondary-button" data-testid="admin-home-refresh">
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} /> Muat ulang
          </button>
        </div>
      </div>

      <div className="section-body">
        <ErrorNotice message={error} onRetry={load} onDismiss={() => setError("")} testId="admin-home-error" />

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <KPICard icon={Banknote} label="Penjualan Hari Ini" value={fmtCur(sales.today)} sub={`${sales.today_orders || 0} pesanan`} color="#007AFF" loading={loading} />
          <KPICard icon={TrendingUp} label="Penjualan MTD" value={fmtCur(sales.mtd)} sub="Bulan berjalan" color="#34C759" loading={loading} />
          <KPICard icon={ArrowUpRight} label="Tertagih MTD" value={fmtCur(sales.collected_mtd)} sub="Kas masuk" color="#30D158" loading={loading} />
          <KPICard icon={Receipt} label="Piutang Belum Lunas" value={fmtCur(ar.outstanding)} sub="Total piutang" color="#5856D6" loading={loading} />
          <KPICard icon={AlertTriangle} label="Piutang Lewat Tempo" value={fmtCur(ar.overdue)} sub="Jatuh tempo lewat" color="#FF3B30" loading={loading} />
          <KPICard icon={Clock} label="Persetujuan Menunggu" value={data?.approvals_pending ?? "—"} sub="Perlu ditindak" color="#FF9500" loading={loading} />
          <KPICard icon={PackageX} label="Stok Rendah" value={lowStock.count ?? "—"} sub="Perlu reorder" color="#FF6B00" loading={loading} />
          <KPICard icon={Award} label="Payout Insentif" value={fmtCur(data?.incentive_payout)} sub="Estimasi MTD" color="#AF52DE" loading={loading} />
        </div>

        {/* FASE G-5 — ringkasan periode yang sedang dibuka (unlock) + sisa waktu */}
        <PeriodUnlockCard onNavigate={onNavigate} />

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          {/* Leaderboard */}
          <div className="rounded-xl border border-[#EFF0F2] bg-white p-4" data-testid="admin-home-leaderboard">
            <div className="flex items-center gap-2 mb-3"><Trophy size={15} className="text-[#FF9500]" /><h3 className="text-[14px] font-bold">Top Sales (MTD)</h3></div>
            {board.length > 0 ? (
              <div className="grid gap-1.5">
                {board.map((r, idx) => (
                  <div key={r.sales_id || idx} className="flex items-center gap-2 py-1.5 border-b border-[#F5F5F7] last:border-0">
                    <span className="text-[11px] font-bold text-[#8E8E93] w-5">{idx + 1}</span>
                    <div className="flex-1 min-w-0"><p className="text-[12px] font-semibold truncate">{r.sales_name}</p>
                      <p className="text-[10.5px] text-[#8E8E93]">{r.orders_count || 0} order • {r.collection_rate || 0}% tertagih</p></div>
                    <span className="text-[12px] font-bold text-[#007AFF] tabular-nums">{fmtCur(r.total_sales)}</span>
                  </div>
                ))}
              </div>
            ) : <div className="h-20 flex items-center justify-center text-[13px] text-[#8E8E93]">Belum ada data penjualan</div>}
          </div>

          {/* Top overdue */}
          <div className="rounded-xl border border-[#EFF0F2] bg-white p-4" data-testid="admin-home-overdue">
            <div className="flex items-center gap-2 mb-3"><AlertTriangle size={15} className="text-[#FF3B30]" /><h3 className="text-[14px] font-bold">Lewat Tempo per Sales</h3></div>
            {overdue.length > 0 && overdue.some((o) => o.overdue_amount > 0) ? (
              <div className="grid gap-1.5">
                {overdue.filter((o) => o.overdue_amount > 0).map((o, idx) => (
                  <div key={idx} className="flex items-center gap-2 py-1.5 border-b border-[#F5F5F7] last:border-0">
                    <div className="flex-1 min-w-0"><p className="text-[12px] font-semibold truncate">{o.sales_name}</p>
                      <p className="text-[10.5px] text-[#8E8E93]">AR {fmtCur(o.ar_outstanding)}</p></div>
                    <span className="text-[12px] font-bold text-red-600 tabular-nums">{fmtCur(o.overdue_amount)}</span>
                  </div>
                ))}
              </div>
            ) : <div className="h-20 flex items-center justify-center text-[13px] text-[#8E8E93]">Tidak ada tagihan lewat tempo 🎉</div>}
          </div>
        </div>

        {/* Low stock */}
        <div className="mt-4 rounded-xl border border-[#EFF0F2] bg-white p-4" data-testid="admin-home-lowstock">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2"><PackageX size={15} className="text-[#FF6B00]" /><h3 className="text-[14px] font-bold">Stok Perlu Reorder</h3></div>
            <button onClick={() => onNavigate && onNavigate("reorder")} className="text-[12px] font-semibold text-[#007AFF]" data-testid="admin-home-goto-reorder">Lihat semua →</button>
          </div>
          {(lowStock.items || []).length > 0 ? (
            <div className="grid gap-1 max-h-64 overflow-auto">
              {lowStock.items.map((it, idx) => (
                <div key={it.product_id || idx} className="grid grid-cols-[1fr_90px_90px] gap-2 text-[12px] py-1.5 border-b border-[#F5F5F7] last:border-0 items-center">
                  <div className="min-w-0"><p className="font-semibold truncate">{it.product_name || it.name}</p>
                    <p className="text-[10px] text-[#8E8E93]">{it.sku || ""}</p></div>
                  <span className="text-right tabular-nums text-[#6B6B73]">Stok fisik {fmt.format(it.on_hand ?? it.available_qty ?? 0)}</span>
                  <span className="text-right tabular-nums font-bold text-[#FF6B00]">ROP {fmt.format(it.reorder_point ?? 0)}</span>
                </div>
              ))}
            </div>
          ) : <div className="h-20 flex items-center justify-center text-[13px] text-[#8E8E93]">Semua stok di atas titik reorder</div>}
        </div>
      </div>
    </section>
  );
}
