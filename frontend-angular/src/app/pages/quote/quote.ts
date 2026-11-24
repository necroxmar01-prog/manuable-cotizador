
import { Component } from '@angular/core';
import {
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators
} from '@angular/forms';

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
  imports: [ReactiveFormsModule],
  templateUrl: './quote.html',
  styleUrl: './quote.scss'
})
export class Quote {
  submitted = false;
  statusMessage = '';

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

    if (this.quoteForm.invalid) {
      this.quoteForm.markAllAsTouched();
      return;
    }

    this.statusMessage =
      'Tus datos son válidos. La conexión con el servicio de cotizaciones está pendiente.';
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
