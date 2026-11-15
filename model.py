import io
import json
import numpy as np
import pandas as pd

SHEET_UNITS = {
    "A표_총거래표(생산자)": "백만원",
    "A표_수입거래표(생산자)": "백만원",
    "A표_국산거래표(생산자)": "백만원",
    "총투입계수(A)": "계수 (투입액/총투입)",
    "수입투입계수(Am)": "계수 (수입투입액/총투입)",
    "국산투입계수(Ad)": "계수 (국산투입액/총투입)",
    "생산유발계수": "계수 (최종수요 1단위당 유발액)",
    "수입유발계수": "계수 (최종수요 1단위당 유발액)",
    "부가가치유발계수": "계수 (최종수요 1단위당 유발액)",
    "최종수요 항목별 생산유발액": "백만원",
    "최종수요 항목별 수입유발액": "백만원",
    "최종수요 항목별 부가가치유발액": "백만원",
}

class IOAnalyzer:
    def __init__(self):
        self.sheets = {}
        self.sectors = []
        self.sector_codes = []
        self.sector_names = []
        self.df_total = None
        self.df_imp = None
        self.df_dom = None
        self.df_a = None
        self.prod_ind = None
        self.imp_ind = None
        self.va_ind = None
        self.fd_prod = None
        self.fd_va = None
        self.fd_imp = None

    def load_excel_bytes(self, file_bytes):
        xls = pd.ExcelFile(io.BytesIO(file_bytes))
        self.sheets = {}
        for name in xls.sheet_names:
            raw = pd.read_excel(xls, sheet_name=name, header=None)
            col_codes = raw.iloc[4, 2:].fillna("").astype(str).str.strip().tolist()
            col_names = raw.iloc[5, 2:].fillna("").astype(str).str.replace("\n", " ").str.strip().tolist()
            data = raw.iloc[6:].copy()
            row_codes = data.iloc[:, 0].fillna("").astype(str).str.strip().tolist()
            row_names = data.iloc[:, 1].fillna("").astype(str).str.replace("\n", " ").str.strip().tolist()
            vals = data.iloc[:, 2:].apply(pd.to_numeric, errors="coerce").fillna(0.0).values
            self.sheets[name] = {
                "row_codes": row_codes,
                "row_names": row_names,
                "col_codes": col_codes,
                "col_names": col_names,
                "values": vals,
                "unit": SHEET_UNITS.get(name, "-")
            }

        t_sheet = self.sheets["A표_총거래표(생산자)"]
        n_sec = t_sheet["row_codes"].index("9590")
        self.sector_codes = t_sheet["row_codes"][:n_sec]
        self.sector_names = t_sheet["row_names"][:n_sec]
        self.sectors = [{"code": c, "name": n} for c, n in zip(self.sector_codes, self.sector_names)]

        self.df_total = t_sheet
        self.df_imp = self.sheets["A표_수입거래표(생산자)"]
        self.df_dom = self.sheets["A표_국산거래표(생산자)"]
        self.df_a = self.sheets["총투입계수(A)"]
        self.prod_ind = self.sheets["생산유발계수"]
        self.imp_ind = self.sheets["수입유발계수"]
        self.va_ind = self.sheets["부가가치유발계수"]
        self.fd_prod = self.sheets["최종수요 항목별 생산유발액"]
        self.fd_va = self.sheets["최종수요 항목별 부가가치유발액"]
        self.fd_imp = self.sheets["최종수요 항목별 수입유발액"]

        return json.dumps({
            "sheet_names": list(self.sheets.keys()),
            "sectors": self.sectors
        }, ensure_ascii=False)

    def get_sheet_rows(self, sheet_name):
        s = self.sheets[sheet_name]
        rows = [{"idx": i, "code": c, "name": n} for i, (c, n) in enumerate(zip(s["row_codes"], s["row_names"]))]
        return json.dumps({"rows": rows, "unit": s["unit"]}, ensure_ascii=False)

    def get_row_values(self, sheet_name, row_idx):
        s = self.sheets[sheet_name]
        r_i = int(row_idx)
        r_code = s["row_codes"][r_i]
        row_vals = s["values"][r_i]
        items = []
        for c, n, v in zip(s["col_codes"], s["col_names"], row_vals):
            unit = s["unit"]
            if r_code == "9801" or c == "9802":
                unit = "지수 (전산업 평균=1.0)"
            elif r_code == "9812":
                unit = "%"
            elif r_code == "9811":
                unit = "계수 (최종수요 1단위당 유발액)"
            items.append({"code": c, "name": n, "value": float(v), "unit": unit})
        return json.dumps({"items": items}, ensure_ascii=False)

    def get_industry_indicators(self, sec_idx):
        idx = int(sec_idx)
        n = len(self.sectors)
        t = self.df_total
        dom = self.df_dom
        imp = self.df_imp

        r_mid = t["row_codes"].index("9590")
        r_va = t["row_codes"].index("9690")
        r_tot_in = t["row_codes"].index("9790")
        r_dom_mid = dom["row_codes"].index("9590")
        r_imp_mid = imp["row_codes"].index("9590")

        c_exp = t["col_codes"].index("9140")
        c_out = t["col_codes"].index("9310")
        c_imp_tot = t["col_codes"].index("9329")
        c_sup_tot = t["col_codes"].index("9390")

        tot_input = t["values"][r_tot_in, idx]
        mid_input = t["values"][r_mid, idx]
        va_val = t["values"][r_va, idx]
        dom_mid = dom["values"][r_dom_mid, idx]
        imp_mid = imp["values"][r_imp_mid, idx]

        export_val = t["values"][idx, c_exp]
        output_val = t["values"][idx, c_out]
        import_val = t["values"][idx, c_imp_tot]
        supply_val = t["values"][idx, c_sup_tot]

        p_s = self.prod_ind
        r_colsum = p_s["row_codes"].index("9590")
        r_power = p_s["row_codes"].index("9801")
        c_sens = p_s["col_codes"].index("9802")

        i_colsum = self.imp_ind["row_codes"].index("9590")
        v_colsum = self.va_ind["row_codes"].index("9590")

        power_val = float(p_s["values"][r_power, idx])
        sens_val = float(p_s["values"][idx, c_sens])

        if power_val >= 1.0 and sens_val >= 1.0:
            l_type = "제1유형 [중간수요적 제조업형]: 영향력지수 ≥ 1.0 & 감응도지수 ≥ 1.0 (전·후방 연쇄효과가 모두 큰 핵심 기간산업)"
        elif power_val >= 1.0 and sens_val < 1.0:
            l_type = "제2유형 [최종수요적 제조업형]: 영향력지수 ≥ 1.0 & 감응도지수 < 1.0 (타 산업 원재료 구매 파급력이 큰 최종재 산업)"
        elif power_val < 1.0 and sens_val >= 1.0:
            l_type = "제3유형 [중간수요적 원시·서비스형]: 영향력지수 < 1.0 & 감응도지수 ≥ 1.0 (타 산업의 중간재로 널리 쓰이는 기초·인프라 산업)"
        else:
            l_type = "제4유형 [최종수요적 원시·서비스형]: 영향력지수 < 1.0 & 감응도지수 < 1.0 (전·후방 연쇄효과가 상대적으로 낮은 독립적 산업)"

        fd = self.fd_prod
        c_9111 = fd["col_codes"].index("9111")
        c_9112 = fd["col_codes"].index("9112")
        c_9121 = fd["col_codes"].index("9121")
        c_9122 = fd["col_codes"].index("9122")
        c_9131 = fd["col_codes"].index("9131")
        c_9132 = fd["col_codes"].index("9132")
        c_9140 = fd["col_codes"].index("9140")
        c_9190 = fd["col_codes"].index("9190")

        fd_tot = fd["values"][idx, c_9190]
        fd_cons = fd["values"][idx, c_9111] + fd["values"][idx, c_9112]
        fd_inv = fd["values"][idx, c_9121] + fd["values"][idx, c_9122] + fd["values"][idx, c_9131] + fd["values"][idx, c_9132]
        fd_exp = fd["values"][idx, c_9140]

        kpis = {
            "총투입(=총산출)": f"{tot_input:,.0f} 백만원",
            "총공급(=총수요)": f"{supply_val:,.0f} 백만원",
            "부가가치율": f"{(va_val / tot_input * 100) if tot_input else 0:.2f} %",
            "중간투입률": f"{(mid_input / tot_input * 100) if tot_input else 0:.2f} %",
            "국산화율 (국산중간재/총중간재)": f"{(dom_mid / mid_input * 100) if mid_input else 0:.2f} %",
            "수입의존도 (수입중간재/총투입)": f"{(imp_mid / tot_input * 100) if tot_input else 0:.2f} %",
            "수출률 (수출액/총산출)": f"{(export_val / output_val * 100) if output_val else 0:.2f} %",
            "수입률 (수입계/총공급)": f"{(import_val / supply_val * 100) if supply_val else 0:.2f} %",
            "생산유발계수 (열합)": f"{p_s['values'][r_colsum, idx]:.4f} (최종수요 1단위당)",
            "부가가치유발계수 (열합)": f"{self.va_ind['values'][v_colsum, idx]:.4f} (최종수요 1단위당)",
            "수입유발계수 (열합)": f"{self.imp_ind['values'][i_colsum, idx]:.4f} (최종수요 1단위당)",
            "영향력계수 (후방연쇄)": f"{power_val:.4f} (지수, 평균=1.0)",
            "감응도계수 (전방연쇄)": f"{sens_val:.4f} (지수, 평균=1.0)",
            "생산의 소비 의존도": f"{(fd_cons / fd_tot * 100) if fd_tot else 0:.2f} %",
            "생산의 투자 의존도": f"{(fd_inv / fd_tot * 100) if fd_tot else 0:.2f} %",
            "생산의 수출 의존도": f"{(fd_exp / fd_tot * 100) if fd_tot else 0:.2f} %"
        }

        a_col = self.df_a["values"][:n, idx]
        top_in_idx = np.argsort(a_col)[::-1][:5]
        top_inputs = [
            {"code": self.sector_codes[i], "name": self.sector_names[i], "val": float(a_col[i])}
            for i in top_in_idx if a_col[i] > 0
        ]

        out_row = t["values"][idx, :n]
        top_out_idx = np.argsort(out_row)[::-1][:5]
        top_outputs = [
            {"code": self.sector_codes[i], "name": self.sector_names[i], "val": float(out_row[i])}
            for i in top_out_idx if out_row[i] > 0
        ]

        return json.dumps({
            "linkage_type": l_type,
            "kpis": kpis,
            "top_inputs": top_inputs,
            "top_outputs": top_outputs
        }, ensure_ascii=False)

    def simulate_demand(self, shocks_json):
        shocks = json.loads(shocks_json)
        n = len(self.sectors)
        f_vec = np.zeros(n)
        for item in shocks:
            f_vec[int(item["idx"])] += float(item["amount"])

        L_prod = self.prod_ind["values"][:n, :n]
        L_va = self.va_ind["values"][:n, :n]
        L_imp = self.imp_ind["values"][:n, :n]

        d_prod = L_prod @ f_vec
        d_va = L_va @ f_vec
        d_imp = L_imp @ f_vec

        rows = []
        for i in range(n):
            if abs(d_prod[i]) > 1e-6 or abs(d_va[i]) > 1e-6 or abs(d_imp[i]) > 1e-6:
                rows.append({
                    "code": self.sector_codes[i],
                    "name": self.sector_names[i],
                    "prod": float(d_prod[i]),
                    "va": float(d_va[i]),
                    "imp": float(d_imp[i])
                })
        rows.sort(key=lambda x: x["prod"], reverse=True)

        return json.dumps({
            "total_shock": float(np.sum(f_vec)),
            "total_prod": float(np.sum(d_prod)),
            "total_va": float(np.sum(d_va)),
            "total_imp": float(np.sum(d_imp)),
            "rows": rows
        }, ensure_ascii=False)

analyzer = IOAnalyzer()
