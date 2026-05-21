import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
// Base URL without /api — for static file downloads served at /generated/
const BASE_URL = API_URL.replace(/\/api$/, "");

export const api = axios.create({
  baseURL: API_URL,
  timeout: 90000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Response interceptor — unwrap FastAPI detail errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      "An unexpected error occurred";
    return Promise.reject(new Error(message));
  }
);

// ─── File helpers ───────────────────────────────────

/** Build a direct download URL for a generated file served as a static asset */
export const getDownloadUrl = (filename: string): string =>
  `${BASE_URL}/generated/${filename}`;

/** Build the API download URL for an invoice by id+type */
export const getInvoiceDownloadUrl = (invoiceId: number, type: "docx" | "pdf"): string =>
  `${API_URL}/invoice/${invoiceId}/download/${type}`;

// ─── API Functions ──────────────────────────────────

export const checkHealth = async (): Promise<{ status: string }> => {
  const response = await api.get("/health");
  return response.data;
};

export const uploadInvoice = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const extractInvoice = async (fileId: string): Promise<ExtractionResult> => {
  // Backend expects file_id as a query param: POST /extract?file_id=xxx
  const response = await api.post(`/extract?file_id=${fileId}`);
  return response.data;
};

export const applyMargin = async (payload: {
  items: ExtractedItem[];
  global_margin_percent: number;
  round_values: boolean;
}): Promise<ApplyMarginResponse> => {
  const response = await api.post("/apply-margin", payload);
  return response.data;
};

export const getDashboard = async (): Promise<DashboardStats> => {
  const response = await api.get("/dashboard");
  return response.data;
};

export const getInvoices = async (skip = 0, limit = 50): Promise<InvoiceListItem[]> => {
  const response = await api.get(`/invoices?skip=${skip}&limit=${limit}`);
  return response.data;
};

export const getInvoice = async (id: number): Promise<InvoiceResponse> => {
  const response = await api.get(`/invoice/${id}`);
  return response.data;
};

export const createInvoice = async (data: InvoiceCreate): Promise<InvoiceResponse> => {
  const response = await api.post("/invoices", data);
  return response.data;
};

export const updateInvoice = async (
  id: number,
  data: Partial<InvoiceCreate>
): Promise<InvoiceResponse> => {
  const response = await api.put(`/invoice/${id}`, data);
  return response.data;
};

export const deleteInvoice = async (id: number): Promise<void> => {
  await api.delete(`/invoice/${id}`);
};

export const generateInvoice = async (
  invoiceId: number,
  format: "docx" | "pdf" | "both"
): Promise<GenerateInvoiceResponse> => {
  const response = await api.post("/generate", { invoice_id: invoiceId, format });
  return response.data;
};

export const getBuyers = async (): Promise<Buyer[]> => {
  const response = await api.get("/buyers");
  return response.data;
};

export const createBuyer = async (data: BuyerCreate): Promise<Buyer> => {
  const response = await api.post("/buyers", data);
  return response.data;
};

// ─── Types ─────────────────────────────────────────

export interface UploadResponse {
  file_id: string;
  filename: string;
  stored_name: string;
  size_bytes: number;
  extension: string;
  message: string;
}

/** Matches backend ExtractedItem schema */
export interface ExtractedItem {
  item_name: string;
  hsn_code: string | null;
  qty: number;
  unit: string | null;
  purchase_rate: number;
  amount: number;
  /** Applied client-side or via /apply-margin */
  margin_percent: number;
  selling_rate: number;
}

/** Matches backend ExtractionResult schema */
export interface ExtractionResult {
  success: boolean;
  method: string;
  items: ExtractedItem[];
  raw_text: string | null;
  warnings: string[];
  confidence: number;
}

export interface ApplyMarginResponse {
  items: ExtractedItem[];
  total_purchase_value: number;
  total_selling_value: number;
  estimated_profit: number;
}

export interface InvoiceItemCreate {
  sr_no: number;
  item_name: string;
  hsn_code: string | null;
  qty: number;
  unit: string;
  purchase_rate: number;
  margin_percent: number;
  selling_rate: number;
  amount: number;
  estimated_profit: number;
}

export interface InvoiceCreate {
  invoice_number: string;
  invoice_date: string;
  buyer_name: string;
  buyer_gst?: string;
  buyer_id?: number;
  country_of_shipment?: string;
  transport_mode?: string;
  port_of_loading?: string;
  port_of_discharge?: string;
  /** TaxMode enum value: "cgst_sgst" | "igst" | "none" */
  tax_mode: "cgst_sgst" | "igst" | "none";
  cgst_percent: number;
  sgst_percent: number;
  igst_percent: number;
  items: InvoiceItemCreate[];
  notes?: string;
  template_id?: number;
}

/** Full invoice response — includes items list and file metadata */
export interface InvoiceResponse {
  id: number;
  invoice_number: string;
  invoice_date: string;
  buyer_name: string;
  buyer_gst?: string;
  buyer_id?: number;
  country_of_shipment?: string;
  transport_mode?: string;
  tax_mode: string;
  cgst_percent: number;
  sgst_percent: number;
  igst_percent: number;
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  total_purchase_value: number;
  estimated_profit: number;
  status: string;
  source_filename?: string;
  docx_filename?: string;
  pdf_filename?: string;
  notes?: string;
  created_at: string;
  updated_at?: string;
  items: InvoiceItemCreate[];
}

/** List view — lightweight, no items array */
export interface InvoiceListItem {
  id: number;
  invoice_number: string;
  invoice_date: string;
  buyer_name: string;
  total_amount: number;
  estimated_profit: number;
  status: string;
  created_at: string;
}

export interface GenerateInvoiceResponse {
  invoice_id: number;
  docx_url: string | null;
  pdf_url: string | null;
  success: boolean;
  message: string;
}

export interface DashboardStats {
  total_invoices: number;
  monthly_invoices: number;
  total_revenue: number;
  monthly_revenue: number;
  estimated_profit: number;
  monthly_profit: number;
  draft_count: number;
  finalized_count: number;
}

export interface BuyerCreate {
  name: string;
  gst_number?: string;
  address?: string;
  email?: string;
  phone?: string;
}

export interface Buyer extends BuyerCreate {
  id: number;
  is_active: boolean;
  created_at?: string;
}
