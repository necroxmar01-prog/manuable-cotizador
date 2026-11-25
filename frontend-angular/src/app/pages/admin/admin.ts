
import { ChangeDetectorRef, Component, inject } from '@angular/core';
import { finalize } from 'rxjs';
import { RouterLink } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { CurrencyPipe, DatePipe } from '@angular/common';
import { FormControl, FormsModule } from '@angular/forms';

import {
  alphanumericAtValidator,
  sanitizeAlphanumericAt
} from '../../shared/input-rules';

import {
  AdminService,
  Lead,
  LeadListResponse,
  QuoteMetrics
} from '../../core/services/admin.service';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [RouterLink, FormsModule, DatePipe, CurrencyPipe],
  templateUrl: './admin.html',
  styleUrl: './admin.scss'
})
export class Admin {
  private readonly adminService = inject(AdminService);
  // La app es zoneless (Angular 21 sin zone.js): las respuestas HTTP no
  // disparan detección de cambios solas, hay que avisarle a Angular.
  private readonly cdr = inject(ChangeDetectorRef);

  username = '';
  password = '';

  leads: Lead[] = [];
  totalLeads = 0;
  metrics: QuoteMetrics | null = null;
  metricsError = '';
  emailFilter = '';

  page = 1;
  pageSize = 20;
  totalPages = 0;

  isLoading = false;
  isAuthenticated = false;
  errorMessage = '';

  login(): void {
    if (!this.username.trim() || !this.password) {
      this.errorMessage = 'Ingresa tu usuario y contraseña.';
      return;
    }

    const usernameErrors = alphanumericAtValidator(
      new FormControl(this.username)
    );

    const passwordErrors = alphanumericAtValidator(
      new FormControl(this.password)
    );

    if (usernameErrors || passwordErrors) {
      this.errorMessage =
        'El usuario y la contraseña solo pueden contener letras sin acentos, números y @.';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    this.adminService.getLeads(
      this.username.trim(),
      this.password,
      this.page,
      this.pageSize
    ).pipe(finalize(() => this.cdr.markForCheck())).subscribe({
      next: (response: LeadListResponse) => {
        this.isAuthenticated = true;
        this.updateDashboard(response);
        this.loadMetrics();
        this.isLoading = false;
      },
      error: (error: HttpErrorResponse) => {
        this.isLoading = false;

        if (error.status === 401) {
          this.errorMessage = 'Usuario o contraseña incorrectos.';
        } else if (error.status === 503) {
          this.errorMessage = 'La autenticación administrativa no está configurada en el servidor.';
        } else {
          this.errorMessage = 'No fue posible consultar los leads. Verifica que el servidor esté disponible.';
        }
      }
    });
  }

  loadPage(page: number): void {
    if (page < 1 || page > this.totalPages || this.isLoading) {
      return;
    }

    this.page = page;
    this.isLoading = true;
    this.errorMessage = '';

    this.adminService.getLeads(
      this.username.trim(),
      this.password,
      this.page,
      this.pageSize,
      this.emailFilter
    ).pipe(finalize(() => this.cdr.markForCheck())).subscribe({
      next: (response: LeadListResponse) => {
        this.updateDashboard(response);
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
        this.errorMessage = 'No fue posible cargar esta página.';
      }
    });
  }

  search(): void {
    this.page = 1;
    this.totalPages = Math.max(this.totalPages, 1);
    this.loadPage(1);
  }

  loadMetrics(): void {
    this.metricsError = '';
    this.adminService.getQuoteMetrics(this.username.trim(), this.password).pipe(finalize(() => this.cdr.markForCheck())).subscribe({
      next: (metrics) => (this.metrics = metrics),
      error: () => (this.metricsError = 'No fue posible cargar las métricas.')
    });
  }

  logout(): void {
    this.username = '';
    this.password = '';
    this.leads = [];
    this.totalLeads = 0;
    this.metrics = null;
    this.emailFilter = '';
    this.totalPages = 0;
    this.page = 1;
    this.isAuthenticated = false;
    this.errorMessage = '';
  }

  private updateDashboard(response: LeadListResponse): void {
    this.leads = response.items;
    this.totalLeads = response.total;
    this.totalPages = response.pages;
  }

  get todayMetrics() {
    return this.metrics?.daily[0] ?? null;
  }

  sanitizeUsername(value: string): void {
    this.username = sanitizeAlphanumericAt(value);
  }

  sanitizePassword(value: string): void {
    this.password = sanitizeAlphanumericAt(value);
  }
}
