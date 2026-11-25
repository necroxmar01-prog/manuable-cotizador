
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import { QuoteOption } from './quote.service';

export interface LeadQuote {
  id: number;
  origin_postal_code: string;
  destination_postal_code: string;
  weight_kg: number | string;
  length_cm?: number | string | null;
  width_cm?: number | string | null;
  height_cm?: number | string | null;
  distance_km: number | string | null;
  zone: number;
  source: 'web' | 'telefono';
  external_ref: string | null;
  created_at: string;
  valid_until: string;
  price_guaranteed: boolean;
  options: QuoteOption[];
}

export interface DailyQuoteMetrics {
  date: string;
  quotes: number;
  without_options: number;
}

export interface QuoteMetrics {
  days: number;
  total_quotes: number;
  total_without_options: number;
  daily: DailyQuoteMetrics[];
}

export interface Lead {
  id: number;
  email: string;
  created_at: string;
  quotes: LeadQuote[];
}

export interface LeadListResponse {
  items: Lead[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

@Injectable({
  providedIn: 'root'
})
export class AdminService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://localhost:8000/api/leads';
  private readonly metricsUrl = 'http://localhost:8000/api/metrics/quotes';

  getLeads(
    username: string,
    password: string,
    page = 1,
    pageSize = 20,
    email = ''
  ): Observable<LeadListResponse> {
    let params = new HttpParams()
      .set('page', page)
      .set('page_size', pageSize);

    if (email.trim()) {
      params = params.set('email', email.trim());
    }

    return this.http.get<LeadListResponse>(this.apiUrl, {
      headers: this.authHeaders(username, password),
      params
    });
  }

  getQuoteMetrics(username: string, password: string, days = 14): Observable<QuoteMetrics> {
    return this.http.get<QuoteMetrics>(this.metricsUrl, {
      headers: this.authHeaders(username, password),
      params: new HttpParams().set('days', days)
    });
  }

  private authHeaders(username: string, password: string): HttpHeaders {
    return new HttpHeaders({
      Authorization: `Basic ${btoa(`${username}:${password}`)}`
    });
  }
}