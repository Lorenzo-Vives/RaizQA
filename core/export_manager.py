import os
import docx.shared
from docx import Document
from datetime import datetime

class ExportManager:
    """Maneja la exportación de datos del proyecto (Diario, Excel, etc) puro, sin dependencias GUI."""

    @staticmethod
    def export_diary(entries, project_name, export_path):
        """Exporta el diario estructurado (lista de diccionarios) a un documento Word."""
        doc = Document()
        doc.add_heading(f"Diario de codificación - {project_name}", level=1)

        if not entries:
            doc.add_paragraph("(Diario vacío)")
        else:
            for entry in entries:
                # 1. Parsear y formatear la fecha
                date_str = entry.get("date", "")
                try:
                    dt = datetime.fromisoformat(date_str)
                    date_formatted = dt.strftime("%d/%m/%Y a las %H:%M")
                except ValueError:
                    date_formatted = date_str  # Fallback por si la fecha está corrupta o en otro formato

                author = entry.get("author", "Desconocido")
                message = entry.get("message", "")

                # 2. Agregar encabezado de la entrada (Autor y Fecha)
                p_header = doc.add_paragraph()
                run = p_header.add_run(f"👤 {author} - {date_formatted}")
                run.bold = True

                # 3. Agregar el cuerpo del mensaje
                doc.add_paragraph(message)
                
                # 4. Agregar línea separadora sutil
                p_divider = doc.add_paragraph()
                run_divider = p_divider.add_run("_" * 50)
                run_divider.font.color.rgb = docx.shared.RGBColor(180, 180, 180) # Gris claro

        doc.save(export_path)

    @staticmethod
    def export_code_tree(rows, export_path):
        """Exporta el libro de códigos (jerarquía) a Excel."""
        import openpyxl
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Libro de códigos"
        
        ExportManager._write_codebook_sheet(ws, rows, title_text="Libro de códigos", frequency_label="Frecuencia")
        wb.save(export_path)

    @staticmethod
    def export_code_fragments(selected_rows, fragment_rows, export_path):
        """Exporta el libro de códigos y sus fragmentos asociados a Excel."""
        import openpyxl

        wb = openpyxl.Workbook()
        
        # Hoja 1: Libro
        ws_codes = wb.active
        ws_codes.title = "Libro de códigos"
        ExportManager._write_codebook_sheet(ws_codes, selected_rows, title_text="Libro de códigos", frequency_label="Fragmentos")
        
        # Hoja 2: Fragmentos
        ws_fragments = wb.create_sheet("Fragmentos")
        ExportManager._write_fragments_sheet(ws_fragments, fragment_rows)
        
        wb.save(export_path)

    @staticmethod
    def _write_codebook_sheet(worksheet, rows, title_text="Libro de códigos", frequency_label="Frecuencia"):
        from openpyxl.styles import Font, PatternFill, Alignment

        header = [title_text, "", "", "", "Memo", frequency_label]
        worksheet.append(header)

        header_fill = PatternFill(start_color="5d9bd3", end_color="5d9bd3", fill_type="solid")
        data_fill = PatternFill(start_color="f6f8fb", end_color="f6f8fb", fill_type="solid")
        bold = Font(bold=True)
        memo_col = 5
        freq_col = 6

        for col_idx in range(1, len(header) + 1):
            cell = worksheet.cell(row=1, column=col_idx)
            cell.font = bold
            cell.fill = header_fill
            cell.alignment = Alignment(vertical="center")

        for row_data in rows:
            level = row_data.get("level", 0)
            total_cols = max(freq_col, 1 + level)
            row = ["" for _ in range(total_cols)]
            name_col = 1 + level
            row[name_col - 1] = row_data.get("name", "")
            
            if memo_col - 1 >= len(row):
                row.extend([""] * (memo_col - len(row)))
            row[memo_col - 1] = row_data.get("memo", "")
            
            if freq_col - 1 >= len(row):
                row.extend([""] * (freq_col - len(row)))
            row[freq_col - 1] = row_data.get("freq", "")
            
            worksheet.append(row)
            current_row = worksheet.max_row
            for col_idx in range(1, freq_col + 1):
                cell = worksheet.cell(row=current_row, column=col_idx)
                cell.fill = data_fill
                cell.alignment = Alignment(vertical="top", wrap_text=True)

        for col_name in ("A", "B", "C", "D"):
            worksheet.column_dimensions[col_name].width = 36
        worksheet.column_dimensions["E"].width = 48
        worksheet.column_dimensions["F"].width = 14

        for row in worksheet.iter_rows(min_row=1, max_row=worksheet.max_row, min_col=1, max_col=freq_col):
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)

    @staticmethod
    def _write_fragments_sheet(worksheet, fragment_rows):
        from openpyxl.styles import Font, PatternFill, Alignment

        header = ["Código", "Documento", "Fragmento", "Memo"]
        worksheet.append(header)

        header_fill = PatternFill(start_color="5d9bd3", end_color="5d9bd3", fill_type="solid")
        data_fill = PatternFill(start_color="f6f8fb", end_color="f6f8fb", fill_type="solid")
        bold = Font(bold=True)

        for col_idx in range(1, len(header) + 1):
            cell = worksheet.cell(row=1, column=col_idx)
            cell.font = bold
            cell.fill = header_fill
            cell.alignment = Alignment(vertical="center")

        for fragment in fragment_rows:
            worksheet.append([
                fragment.get("code_name", ""),
                fragment.get("document", ""),
                fragment.get("text", ""),
                fragment.get("memo", ""),
            ])
            current_row = worksheet.max_row
            for col_idx in range(1, len(header) + 1):
                cell = worksheet.cell(row=current_row, column=col_idx)
                cell.fill = data_fill
                cell.alignment = Alignment(vertical="top", wrap_text=True)

        worksheet.column_dimensions["A"].width = 28
        worksheet.column_dimensions["B"].width = 28
        worksheet.column_dimensions["C"].width = 100
        worksheet.column_dimensions["D"].width = 48
