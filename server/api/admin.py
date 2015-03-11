import csv
import os

from flask import Blueprint, request, render_template, redirect, flash
from flask import send_from_directory
from flask import current_app as app

from server.constants import EXPLANATION_TYPE_IDENTIFIERS
from server.db import Finding, Explanation, FindingWeight
from server.helpers import success, failure
from server.helpers.data import parse_csv
from werkzeug import secure_filename

admin_api = Blueprint( 'admin_api', __name__ )


def allowed_file( filename ):
    return '.' in filename and \
        filename.rsplit( '.', 1 )[1] in app.config[ 'ALLOWED_EXTENSIONS' ]


@admin_api.route( '/' )
def admin_index():
    '''
        admin_index

        Returns the 10 latest explanations entered into the database
    '''

    page = int( request.args.get( 'page', 1 ) )

    explanations = Explanation.query.ascending( Explanation.name ).paginate( page=page,
                     per_page=100 )
    return render_template( '/admin/browse.html', pagination=explanations )


@admin_api.route( '/csv_upload', methods=[ 'POST' ] )
def csv_upload():
    '''
        csv_upload

        Parse and add data from the CSV to the database
    '''
    if request.method != 'POST':
        return redirect( '/admin/manage' )

    file = request.files[ 'file' ]
    if file and allowed_file( file.filename ):
        filename = secure_filename( 'tmp.csv' )
        tmp_file = os.path.join( app.config[ 'UPLOAD_FOLDER' ], filename )
        file.save( tmp_file )

        # Now process the sucker!
        errors = parse_csv( tmp_file )
        print errors

        if len( errors ) > 0:
            for error in errors:
                flash( error, 'error' )
            # For some reason flash() is not working right now.  For now I'll just use failure()
            failure(errors)
        else:
            flash( 'File uploaded and parsed successfully!', 'success' )

        # Remove the tmp file
        os.remove( tmp_file )

    return redirect( '/admin/manage' )


@admin_api.route( '/csv_download', methods=[ 'GET' ] )
def csv_download():
    '''
        csv_download

        Queries the database for ALL explanations and returns the results as a
        CSV to be edited. The CSV will be sorted by explanation name.

        The format in which the csv will as follows:
        <explanation id>, <explanation name>, <finding 1>, <finding 2>, ...

        The findings will be formatted as such:
        <finding name>:<finding weight>

        Thus for example, the following could be outputted as a CSV:

        43ae01, Explanation1, male:0.5, cough:1
        43ae02, Explanation2, cough:0.25, elderly:0.50, fever:0.25

    '''

    # Query all the explanations
    explanations = Explanation.query.ascending( Explanation.name ).all()

    # Write it out to a CSV file
    directory = os.path.join( app.config[ 'UPLOAD_FOLDER' ], 'doknosis.csv' )
    csvWriter = csv.writer( open( directory, 'wb' ) )

    for explanation in explanations:
        row = [ explanation.mongo_id, explanation.name ]

        for finding in explanation.findings:
            row.append( '%s:%f' % ( finding.name, finding.weight ) )

        csvWriter.writerow( row )

    # Deliver the CSV file to the user
    return send_from_directory( app.config[ 'UPLOAD_FOLDER' ], 'doknosis.csv' )


@admin_api.route( '/manage', methods=[ 'GET' ] )
def manage_explanations():
    '''
        manage_explanations

        Gives an admin the option of downloading the CSV database and/or
        uploading a CSV database to update current one.
    '''
    return render_template( '/admin/manage.html' )


@admin_api.route( '/add/explanation', methods=[ 'GET' ] )
def add_explanation():
    '''
        add_explanations

        Adds a explanation to the database ( if it doesn't already exist ).
        Redirects to the edit page with the new ( or existing ) explanation.

        @param name - Explanation name
    '''
    explanation_name = request.args.get( 'name' ).strip().capitalize()
    explanation_type_id = request.args.get( 'type_identifier' )
    if explanation_type_id is None:
        # Default starting point
        explanation_type_id = 'Disease'
    else:
        explanation_type_id = explanation_type_id.strip().capitalize()

    if explanation_type_id not in EXPLANATION_TYPE_IDENTIFIERS:
        return failure('Invalid explanation type {} (must be one of {})!'.format(explanation_type_id,EXPLANATION_TYPE_IDENTIFIERS))

    # Query the database for the explanation information
    explanation = Explanation.query.filter( {'name': explanation_name} ).first()
    findings = []

    # Check to see if it already exists.
    if explanation is None:
        explanation = Explanation( name=explanation_name, type_identifier=explanation_type_id )
        explanation.save()
    else:
        if explanation.type_identifier != explanation_type_id:
            return failure('Explanation with name {} already exists, but type in database is {}, not {}!'.format(explanation_name, 
                                                                                                                  explanation.type_identifier,
                                                                                                                  explanation_type_id))
        # If the explanations exists, create a findings list to show on the
        # edit page
        findings_list = explanation.findings
        findings = [ x.to_dict() for x in findings_list ]

    return render_template( 'edit.html', explanation=explanation, findings=findings )


@admin_api.route( '/save/explanation/<explanation_id>' )
def save_explanation( explanation_id ):
    '''
        save_explanation

        Create a explanation if it doesn't already exist

        @param name - Explanation name
    '''
    explanation_name = request.args.get( 'name', None )
    if explanation_name is None:
        return failure( 'Invalid Explanation Name' )
    explanation_name = explanation_name.strip().capitalize()

    explanation_type_id = request.args.get( 'type_identifier', None )
    if explanation_type_id is None:
        return failure( 'Invalid Explanation Type' )
    explanation_type_id = explanation_type_id.strip().capitalize()
    if explanation_type_id not in EXPLANATION_TYPE_IDENTIFIERS:
        return failure('Invalid explanation type {} (must be one of {})!'.format(explanation_type_id,EXPLANATION_TYPE_IDENTIFIERS))


    try:
        explanation = Explanation.query.filter(Explanation.mongo_id == explanation_id).first()
    except Exception:
        return failure( 'Invalid Explanation ID' )

    if explanation is None:
        return failure( 'Invalid Explanation ID' )

    explanation.name = explanation_name
    explanation.type_identifier = explanation_type_id
    explanation.save()

    return success()


@admin_api.route( '/delete/explanation/<explanation_id>', methods=[ 'GET' ] )
def delete_explanation( explanation_id ):
    '''
        delete_explanation

        Deletes a explanation from the database

        @param explanation_id - Explanation MongoDB id
    '''
    try:
        explanation = Explanation.query.filter(Explanation.mongo_id == explanation_id).first()
    except Exception:
        # Invalid explanation id, just send back to admin page.
        return redirect( '/admin' )

    if explanation is not None:
        explanation.remove()

    return redirect( '/admin' )


@admin_api.route( '/add/<explanation_id>/finding', methods=[ 'POST' ] )
def add_finding( explanation_id ):
    '''
        add_finding

        Add a finding ( name & weight ) to a explanation

        @param explanation_id   - Explanation MongoDB id
        @param name         - Finding name
        @param weight       - Finding weight
    '''
    finding_name = request.form.get( 'name', None )

    if finding_name is None:
        return failure( 'Invalid Finding Name' )

    finding_name = finding_name.strip().lower()
    try:
        weight       = float( request.form[ 'weight' ] )
    except ValueError:
        return failure( 'Invalid Finding Weight' )

    # Find the explanation to add this finding too
    explanation = Explanation.query.filter( Explanation.mongo_id == explanation_id ).first()

    # Check our findings list to see if we have this finding already or not
    finding = Finding.query.filter( Finding.name == finding_name ).first()

    # Add this finding to the findings list
    if finding is None:
        finding = Finding( name=finding_name )
        finding.save()

    # Add this finding to the explanation
    explanation.findings.append(FindingWeight( name=finding_name, weight=weight ))
    explanation.save()

    return success()


@admin_api.route( '/delete/<explanation_id>/finding/', methods=[ 'POST' ] )
def delete_empty_finding( explanation_id ):
    '''
        delete_empty_finding

        If for some reason a finding's name is empty ( by accident or in the
        CSV ) This method helps alleviate that corner case. Calls
        delete_finding with an empty finding_id

        @param explanation_id - Explanation MongoDB id
    '''
    return delete_finding( explanation_id, '' )


@admin_api.route('/delete/<explanation_id>/finding/<finding_id>', methods=['POST'])
def delete_finding( explanation_id, finding_id ):
    '''
        delete_finding

        Deletes a finding from a explanation instance

        @param explanation_id - Explanation MongoDB id
        @param finding_id - Finding id
    '''
    try:
        explanation = Explanation.query.filter(Explanation.mongo_id == explanation_id).first()
    except Exception:
        return failure( 'Invalid Explanation ID' )

    # Find finding and remove it
    for find in explanation.findings:
        if find.name == finding_id:
            explanation.findings.remove( find )
            break
    explanation.save()

    # Also check if this finding no longer exists in the db.
    count = Explanation.query.filter({'findings.name': finding_id}).count()
    if count == 0:
        # Remove from findings list
        finding = Finding.query.filter( Finding.name == finding_id ).first()
        finding.remove()

    return success()


@admin_api.route( '/edit/<explanation_id>')
def edit_explanation( explanation_id ):
    '''
        edit_explanation

        Queries a explanation by its MongoDB id and returns the edit page for that
        explanation.

        @param explanation_id - Explanation MongoDB id
    '''
    explanation = Explanation.query.filter( Explanation.mongo_id == explanation_id ).first()
    findings = [ x.to_dict() for x in explanation.findings ]

    return render_template( 'edit.html', explanation=explanation, findings=findings )


@admin_api.route('/delete_all_of_type', methods=['POST'])
def delete_all_of_type( ):
    '''
        delete_all_of_type

        Deletes all explanation entries of given type (specified by drop-down menu)

    '''

    explanation_type_id = request.args.get( 'type_identifier' )
    if explanation_type_id is None:
        return failure('Tried to delete all with no type specified!')

    explanation_type_id = explanation_type_id.strip().capitalize()

    # Query the database for the explanation information
    if explanation_type_id in EXPLANATION_TYPE_IDENTIFIERS:
        explanations = Explanation.query.filter( {'type_identifier':explanation_type_id} )
    elif explanation_type_id == 'All':
        explanations = Explanation.query.filter()
    else:
        return failure('Tried to delete all explanations of type {} (must be one of {})!'.format(explanation_type_id,EXPLANATION_TYPE_IDENTIFIERS+['All']))

    # This is a test:
    return failure('Would have deleted {} entries!'.format(len(explanations)))

    for explanation in explanations:
        if explanation is not None:
            explanation.remove()

    return success()
