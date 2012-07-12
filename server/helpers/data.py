import csv

from server.db import Disease, FindingWeight


def _parse_findings( disease_findings, errors, line_no ):
    findings = []

    finding_parse_error = False

    # Parse the findings
    for finding in disease_findings:
        if ':' not in finding:
            errors.append( 'Line %d: Invalid finding format'
                            % ( line_no ) )
            finding_parse_error = True
            break

        name, weight = finding.split( ':' )
        findings.append( FindingWeight( name=name, weight=weight ) )

    return ( finding_parse_error, findings )


def parse_csv( file ):
    errors = []

    reader = csv.reader( open( file, 'rb' ) )

    line_no = 0
    for disease in reader:
        line_no += 1

        if len( disease ) < 2:
            errors.append( 'Line %d: Must have an ID ( can be blank )'
                            ' and disease name' % ( line_no ) )
            continue

        disease_id          = disease[0].strip()
        disease_name        = disease[1].strip().capitalize()

        if len( disease_name ) == 0:
            errors.append( 'Line %d: Invalid Disease Name' % ( line_no ) )
            continue

        disease_findings    = [ ':0.5' ]  # All diseases have a default weight.
        if len( disease ) > 2:
            disease_findings    = disease[2:]

        has_id = len( disease_id ) != 0

        if has_id:
            # Attempt to find disease from id
            disease = None
            try:
                disease = Disease.query.filter(Disease.mongo_id == disease_id)
            except Exception:
                errors.append( 'Line %d: Invalid Disease ID' % ( line_no ) )
                continue

            # If we have an invalid disease id, log the error and continue
            if disease == None:
                errors.append( 'Line %d: Invalid Disease ID' % ( line_no ) )
                continue

            # Parse the findings
            finding_parse_error, findings = _parse_findings( disease_findings,
                                                             errors,
                                                             line_no )

            # Only save finding data if there are no errors parsing the
            # findings
            if not finding_parse_error and len( errors ) == 0:
                disease.findings = findings
                disease.save()
        else:
            # Parse the findings
            finding_parse_error, findings = _parse_findings( disease_findings,
                                                             errors,
                                                             line_no )

            # Only save the new disease if there are no errors parsing the
            # findings
            if not finding_parse_error and len( errors ) == 0:
                disease = Disease( name=disease_name )
                disease.findings = findings
                disease.save()
    return errors
