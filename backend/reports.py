from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.db import aware
from backend.images import fetch_report_image
from backend.vehicle_photos import generic_photo
from ml.features import FEATURES


def prediction_pdf(prediction, settings, image_metadata=None, photo_bytes=None):
    output = BytesIO()
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    def paragraph(value, style=body):
        return Paragraph(escape(str(value)), style)
    story = [paragraph("SmartSauda | Vehicle valuation", styles["Title"]),
             paragraph(f"Report {prediction.id}"),
             paragraph(f"Created {aware(prediction.created_at).isoformat()} | Nepal | Model {prediction.model_version}"),
             Spacer(1, 12), paragraph(f"Estimated resale price: NPR {prediction.price:,.2f}", styles["Heading1"])]
    ignored = prediction.result.get('ignored_input_fields', [])
    if ignored:
        story.extend([paragraph('Inputs not used for this price', styles['Heading2']),
                      paragraph('These supplied inputs did not influence the estimate: ' + ', '.join(field.replace('_', ' ') for field in ignored))])
    if prediction.result.get('reference_year'):
        story.append(paragraph(f"Age reference year: {prediction.result['reference_year']}. Historical prices are not adjusted to today's market."))
    metadata = image_metadata if image_metadata is not None else prediction.image
    photo = photo_bytes or fetch_report_image(metadata, settings.image_download_hosts)
    if not photo:
        metadata = generic_photo(prediction.vehicle_type)
        photo = fetch_report_image(metadata, settings.image_download_hosts)
    if photo:
        image = Image(BytesIO(photo))
        image._restrictSize(4.5 * inch, 2.4 * inch)
        label = (f"Generic {prediction.vehicle_type.lower()} photo: {metadata.get('depicted_model', '')}. Selected model is not pictured."
                 if metadata.get("match_kind") == "category" else
                 "Representative studio render (CarImages free tier watermark); closest model/year may differ."
                 if metadata.get("match_kind") == "render" else "Representative vehicle photo; year, variant and condition may differ.")
        story.extend([image, paragraph(label), paragraph("Image displayed without cropping or editing."),
                      paragraph(f"{metadata.get('title', 'Vehicle photo')} - {metadata.get('author', '')}"),
                      paragraph(f"Image source: {metadata.get('attribution_url', '')}"),
                      paragraph(f"License: {metadata.get('license', 'See source')} {metadata.get('license_url', '')}")])
    else:
        story.append(paragraph("Photo temporarily unavailable."))
    story.extend([Spacer(1, 12), paragraph("Submitted specifications", styles["Heading2"])])
    supported = {'vehicle_type', 'manufacture_year', 'km_driven', *FEATURES[prediction.vehicle_type]['numeric'], *FEATURES[prediction.vehicle_type]['categorical']}
    rows = [[paragraph(key.replace("_", " ").title()), paragraph(value)]
            for key, value in prediction.specifications.items() if value is not None and key in supported]
    table = Table(rows, colWidths=[180, 320], hAlign="LEFT")
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.whitesmoke, colors.white]),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.extend([table, Spacer(1, 12), paragraph("Limitations", styles["Heading2"])])
    for warning in prediction.result["warnings"]:
        story.append(paragraph(warning["message"]))
    story.append(paragraph("This historical-data estimate is not an appraisal or a guaranteed sale price. Inspect the vehicle and compare current local listings."))
    SimpleDocTemplate(output, title="SmartSauda vehicle valuation", author="SmartSauda",
                      rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=42).build(story)
    return output.getvalue()
