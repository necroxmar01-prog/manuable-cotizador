import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface QuoteRequest {
  origin_postal_code: string;
  destination_postal_code: string;
  weight_kg: number;
  email: string;
  length_cm?: number;
  width_cm?: number;
  height_cm?: number;
}

export interface QuoteOption {
  carrier_name: string;
  service_type: string;
  price_mxn: number | string;
  delivery_days_min: number | null;
  delivery_days_max: number | null;
  billable_weight_kg?: number | string | null;
  weight_method?: 'real' | 'volumetrico' | null;
}

export interface QuoteResponse {
  id: number;
  origin_postal_code: string;
  destination_postal_code: string;
  weight_kg: number | string;
  distance_km: number | string | null;
  zone: number;
  created_at: string;
  valid_until: string;
  options: QuoteOption[];
  notices: string[];
}

@Injectable({
  providedIn: 'root'
})
export class QuoteService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://localhost:8000/api/quotes';

  createQuote(request: QuoteRequest): Observable<QuoteResponse> {
    return this.http.post<QuoteResponse>(this.apiUrl, request);
  }
}
