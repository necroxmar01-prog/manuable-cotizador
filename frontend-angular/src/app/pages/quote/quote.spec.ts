import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { Quote } from './quote';

describe('Cotizador (fase 2)', () => {
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Quote],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  function type(el: HTMLInputElement, value: string) {
    el.value = value;
    el.dispatchEvent(new Event('input'));
  }

  it('acepta un CP pegado con espacios y avisa si escriben la ciudad', () => {
    const fixture = TestBed.createComponent(Quote);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    const origin = root.querySelector<HTMLInputElement>('#originPostalCode')!;

    type(origin, ' 06600 ');
    fixture.detectChanges();
    expect(fixture.componentInstance.originPostalCode.value).toBe('06600');

    type(origin, 'Monterrey');
    fixture.detectChanges();
    expect(root.textContent).toContain('no el nombre de la ciudad');
  });

  it('envía medidas y muestra folio, vigencia y avisos', async () => {
    const fixture = TestBed.createComponent(Quote);
    const component = fixture.componentInstance;
    fixture.autoDetectChanges();
    await fixture.whenStable();
    component.quoteForm.setValue({
      originPostalCode: '06600',
      destinationPostalCode: '64000',
      weight: '2',
      length: '40',
      width: '30',
      height: '30',
      email: 'ana@tienda.mx'
    });

    (fixture.nativeElement as HTMLElement).querySelector('form')!
      .dispatchEvent(new Event('submit'));
    await fixture.whenStable();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Consultando');
    const request = http.expectOne('http://localhost:8000/api/quotes');
    expect(request.request.body).toMatchObject({ length_cm: 40, width_cm: 30, height_cm: 30 });

    request.flush({
      id: 42, origin_postal_code: '06600', destination_postal_code: '64000', weight_kg: '2',
      distance_km: '706', zone: 3, created_at: '2026-12-01T10:00:00-06:00',
      valid_until: '2026-12-31T23:59:59-06:00',
      options: [{ carrier_name: 'DHL', service_type: 'aéreo', price_mxn: '1171.58',
        delivery_days_min: 3, delivery_days_max: 3, billable_weight_kg: '7.200', weight_method: 'volumetrico' }],
      notices: []
    });
    // Sin detectChanges manual: la app es zoneless y debe refrescarse sola.
    await fixture.whenStable();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Folio #42');
    expect(text).toContain('31/12/2026');
    expect(text).toContain('Se cobra por tamaño de caja: 7.2 kg');
    expect(text).not.toContain('Consultando');
  });

  it('muestra el mensaje del backend en errores de validación', () => {
    const fixture = TestBed.createComponent(Quote);
    const component = fixture.componentInstance;
    component.quoteForm.setValue({
      originPostalCode: '06600', destinationPostalCode: '64000', weight: '2',
      length: '10', width: '10', height: '10', email: 'ana@tienda.mx'
    });

    component.onSubmit();
    http.expectOne('http://localhost:8000/api/quotes').flush(
      { detail: 'El código postal debe tener 5 dígitos.' },
      { status: 422, statusText: 'Unprocessable' }
    );

    expect(component.errorMessage).toBe('El código postal debe tener 5 dígitos.');
  });

  it('no menciona el volumétrico cuando gana el peso real', () => {
    const component = TestBed.createComponent(Quote).componentInstance;
    const option = { weight_method: 'volumetrico', billable_weight_kg: '8.000' };

    expect(component.chargedByVolume(option, '8.000')).toBe(false);
    expect(component.chargedByVolume({ ...option, billable_weight_kg: '7.200' }, '2')).toBe(true);
    expect(component.chargedByVolume({ weight_method: 'real', billable_weight_kg: '2' }, '2')).toBe(false);
  });
});
