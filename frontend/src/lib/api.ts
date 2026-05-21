import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export const api = axios.create({
  baseURL: API_URL,
  timeout: 60000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor
api.interceptors.request.use((config) => {
  return config;
});

// Response interceptor for error handling
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

// ─── API Functions ─────────────────────────────────

export const uploadInvoice = async (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const extractInvoice = async (fileId: string) => {
  const response = await api.post(`/extract?file_id=${fileId}`);
  return response.data;
};

export const applyMargin = async (payload: {
  items: ExtractedItem[];
  global_margin_percent: number;
  round_values: boolean;
}) => {
  const response = await api.post("/apply-margin", payload);
  return response.data;
};

export const getDashboard = async () => {
  const response = await api.get("/dashboard");
  return response.data;
};

export const getInvoices = async (skip = 0, limit = 50) => {
  const response = await api.get(`/invoices?skip=${skip}&limit=${limit}`);
  return response.data;
};

export const getInvoice = async (id: number) => {
  const response = await api.get(`/invoice/${id}`);
  return response.data;
};

export const createInvoice = async (data: InvoiceCreate) => {
  const response = await api.post("/invoices", data);
  return response.data;
};

export const updateInvoice = async (id: number, data: Partial<InvoiceCreate>) => {
  const response = await api.put(`/invoice/${id}`, data);
  return response.data;
};

export const deleteInvoice = async (id: number) => {
  await api.delete(`/invoice/${id}`);
};

export const generateInvoice = async (invoiceId: number, format: "docx" | "pdf" | "both") => {
  const response = await api.post("/generate", { invoice_id: invoiceId, format });
  return response.data;
};

export const getBuyers = async () => {
  const response = await api.get("/buyers");
  return response.data;
};

export const createBuyer = async (data: BuyerCreate) => {
  const response = await api.post("/buyers", data);
  return response.data;
};

// ─── Types ─────────────────────────────────────────

export interface ExtractedItem {
  item_name: string;
  hsn_code: string | null;
  qty: number;
  unit: string;
  purchase_rate: number;
  margin_percent: number;
  selling_rate: number;
  amount: number;
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
  tax_mode: "cgst_sgst" | "igst" | "none";
  cgst_percent: number;
  sgst_percent: number;
  igst_percent: number;
  items: InvoiceItemCreate[];
  notes?: string;
}

export interface InvoiceResponse {
  id: number;
  invoice_number: string;
  invoice_date: string;
  buyer_name: string;
  buyer_gst?: string;
  country_of_shipment?: string;
  transport_mode?: string;
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  total_purchase_value: number;
  estimated_profit: number;
  status: string;
  docx_filename?: string;
  pdf_filename?: string;
  created_at: string;
  items: InvoiceItemCreate[];
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
}
