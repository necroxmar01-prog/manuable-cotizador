import { Component, inject } from '@angular/core';
import {
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';

import { QuoteService, QuoteResponse } from '../../core/services/quote.service';
import { CurrencyPipe } from '@angular/common';

import {
  postalCodeValidator,
  positiveDecimalValidator,
  emailFormatValidator,
  sanitizeEmail as sanitizeEmailValue,
  sanitizePostalCode as sanitizePostalCodeValue,
  sanitizeWeight as sanitizeWeightValue
} from '../../shared/input-rules';

@Component({
  selector: 'app-quote',
  standalone: true,
  imports: [ReactiveFormsModule, CurrencyPipe],
  templateUrl: './quote.html',
  styleUrl: './quote.scss'
})
export class Quote {
  private readonly quoteService = inject(QuoteService);

  submitted = false;
  isLoading = false;
  statusMessage = '';
  errorMessage = '';
  quoteResult: QuoteResponse | null = null;

  quoteForm = new FormGroup({
    originPostalCode: new FormControl('', [
      Validators.required,
      postalCodeValidator
    ]),
    destinationPostalCode: new FormControl('', [
      Validators.required,
      postalCodeValidator
    ]),
    weight: new FormControl<string | null>('', [
      Validators.required,
      positiveDecimalValidator
    ]),
    email: new FormControl('', [
      Validators.required,
      Validators.email,
      Validators.maxLength(254),
      emailFormatValidator
    ])
  });

  sanitizePostalCode(
    controlName: 'originPostalCode' | 'destinationPostalCode',
    event: Event
  ): void {
    const input = event.target as HTMLInputElement;
    const sanitized = sanitizePostalCodeValue(input.value);

    input.value = sanitized;
    this.quoteForm.controls[controlName].setValue(sanitized);
  }

  sanitizeWeight(event: Event): void {
    const input = event.target as HTMLInputElement;
    const sanitized = sanitizeWeightValue(input.value);

    input.value = sanitized;
    this.quoteForm.controls.weight.setValue(sanitized);
  }

  sanitizeEmail(event: Event): void {
    const input = event.target as HTMLInputElement;
    const sanitized = sanitizeEmailValue(input.value);

    input.value = sanitized;
    this.quoteForm.controls.email.setValue(sanitized);
  }

  onSubmit(): void {
    this.submitted = true;
    this.statusMessage = '';
    this.errorMessage = '';
    this.quoteResult = null;

    if (this.quoteForm.invalid) {
      this.quoteForm.markAllAsTouched();
      return;
    }

    const formValue = this.quoteForm.getRawValue();

    this.isLoading = true;

    this.quoteService.createQuote({
      origin_postal_code: formValue.originPostalCode ?? '',
      destination_postal_code: formValue.destinationPostalCode ?? '',
      weight_kg: Number(formValue.weight),
      email: formValue.email ?? ''
    }).subscribe({
      next: (response) => {
        this.quoteResult = response;
        this.statusMessage = 'Tu cotización se generó correctamente.';
        this.isLoading = false;
      },
      error: (error) => {
        const detail = error.error?.detail;

        this.errorMessage = typeof detail === 'string'
          ? detail
          : 'No fue posible generar la cotización. Verifica tus datos e inténtalo nuevamente.';

        this.isLoading = false;
      }
    });
  }

  get originPostalCode() {
    return this.quoteForm.controls.originPostalCode;
  }

  get destinationPostalCode() {
    return this.quoteForm.controls.destinationPostalCode;
  }

  get weight() {
    return this.quoteForm.controls.weight;
  }

  get email() {
    return this.quoteForm.controls.email;
  }
}
