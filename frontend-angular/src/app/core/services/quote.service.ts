import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface QuoteRequest {
  origin_postal_code: string;
  destination_postal_code: string;
  weight_kg: number;
  email: string;
}

export interface QuoteOption {
  carrier_name: string;
  service_type: string;
  price_mxn: number | string;
  delivery_days_min: number;
  delivery_days_max: number;
}

export interface QuoteResponse {
  id: number;
  origin_postal_code: string;
  destination_postal_code: string;
  weight_kg: number | string;
  distance_km: number | string;
  zone: number;
  options: QuoteOption[];
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
