import { ChangeDetectorRef, Component, inject } from '@angular/core';
import { finalize } from 'rxjs';
import {
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';

import { QuoteService, QuoteResponse } from '../../core/services/quote.service';
import { CurrencyPipe, DatePipe, DecimalPipe } from '@angular/common';

import {
  postalCodeValidator,
  positiveDecimalValidator,
  emailFormatValidator,
  sanitizeEmail as sanitizeEmailValue,
  sanitizePostalCode as sanitizePostalCodeValue,
  sanitizeWeight as sanitizeWeightValue,
  sanitizeDimension as sanitizeDimensionValue,
  dimensionValidator,
  containsLetters
} from '../../shared/input-rules';

type PostalField = 'originPostalCode' | 'destinationPostalCode';
type DimensionField = 'length' | 'width' | 'height';

@Component({
  selector: 'app-quote',
  standalone: true,
  imports: [ReactiveFormsModule, CurrencyPipe, DatePipe, DecimalPipe],
  templateUrl: './quote.html',
  styleUrl: './quote.scss'
})
export class Quote {
  private readonly quoteService = inject(QuoteService);
  // La app es zoneless (Angular 21 sin zone.js): las respuestas HTTP no
  // disparan detección de cambios solas, hay que avisarle a Angular.
  private readonly cdr = inject(ChangeDetectorRef);

  submitted = false;
  isLoading = false;
  statusMessage = '';
  errorMessage = '';
  quoteResult: QuoteResponse | null = null;
  /** Aviso cuando escriben letras (p. ej. la ciudad) en un campo de CP. */
  readonly dimensionFields: { name: DimensionField; label: string }[] = [
    { name: 'length', label: 'Largo' },
    { name: 'width', label: 'Ancho' },
    { name: 'height', label: 'Alto' }
  ];

  postalHints: Record<PostalField, boolean> = {
    originPostalCode: false,
    destinationPostalCode: false
  };

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
    length: new FormControl<string | null>('', [Validators.required, dimensionValidator]),
    width: new FormControl<string | null>('', [Validators.required, dimensionValidator]),
    height: new FormControl<string | null>('', [Validators.required, dimensionValidator]),
    email: new FormControl('', [
      Validators.required,
      Validators.email,
      Validators.maxLength(254),
      emailFormatValidator
    ])
  });

  sanitizePostalCode(controlName: PostalField, event: Event): void {
    const input = event.target as HTMLInputElement;
    const sanitized = sanitizePostalCodeValue(input.value);

    this.postalHints[controlName] = containsLetters(input.value);
    input.value = sanitized;
    this.quoteForm.controls[controlName].setValue(sanitized);
  }

  sanitizeDimension(controlName: DimensionField, event: Event): void {
    const input = event.target as HTMLInputElement;
    const sanitized = sanitizeDimensionValue(input.value);

    input.value = sanitized;
    this.quoteForm.controls[controlName].setValue(sanitized);
  }

  /** Solo se menciona el volumétrico cuando de verdad aumentó el peso cobrado. */
  chargedByVolume(
    option: { weight_method?: string | null; billable_weight_kg?: number | string | null },
    realWeightKg: number | string
  ): boolean {
    return option.weight_method === 'volumetrico'
      && Number(option.billable_weight_kg) > Number(realWeightKg);
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
      length_cm: Number(formValue.length),
      width_cm: Number(formValue.width),
      height_cm: Number(formValue.height),
      email: formValue.email ?? ''
    }).pipe(finalize(() => this.cdr.markForCheck())).subscribe({
      next: (response) => {
        this.quoteResult = response;
        this.statusMessage = 'Tu cotización se generó correctamente.';
        this.isLoading = false;
      },
      error: (error) => {
        const detail = error.error?.detail;

        this.errorMessage = error.status === 0
          ? 'No pudimos conectar con el cotizador. Revisa tu conexión e inténtalo de nuevo.'
          : typeof detail === 'string'
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

  get length() {
    return this.quoteForm.controls.length;
  }

  get width() {
    return this.quoteForm.controls.width;
  }

  get height() {
    return this.quoteForm.controls.height;
  }

  get email() {
    return this.quoteForm.controls.email;
  }
}
