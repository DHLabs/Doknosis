import csv

from server.db import Disease, FindingWeight


def _parse_findings( disease_findings, errors, line_no ):
    findings = []

    finding_parse_error = False

    # Parse the findings
    for finding in disease_findings:
        spl=finding.split(':')
        if len(spl) < 2:
            # Ignore any finding which does not have an associated prevalence.  Assume these are just comments, so we will not return an error.
            continue
        else:
            name = ':'.join(spl[:-1]).lower()
            try:
                weight = float(spl[-1])
                if weight > 1 or weight < 0:
                    # If a finding has an invalid prevalence number, spit out a warning and ignore it.
                    print('Warning -- Finding \"{}\", prevalence weight ({}) not in [0,1].  Ignoring this finding.'.format(name,weight))
                    finding_parse_error = True
                    break

            except ValueError:
                # If prevalence value is not a probability, skip this finding!
                print('Warning -- Finding \"{}\", prevalence weight ({}) not a number.  Ignoring this finding.'.format(name,spl[-1]))
                finding_parse_error = True
                break

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
