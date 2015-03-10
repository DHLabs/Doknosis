import csv
import os

from flask import Blueprint, request, render_template, redirect, flash
from flask import send_from_directory
from flask import current_app as app

from server.db import Finding, Disease, FindingWeight
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

        Returns the 10 latest diseases entered into the database
    '''

    page = int( request.args.get( 'page', 1 ) )

    diseases = Disease.query.ascending( Disease.name ).paginate( page=page,
                     per_page=100 )
    return render_template( '/admin/browse.html', pagination=diseases )


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
        # print errors

        if len( errors ) > 0:
            for error in errors:
                flash( error, 'error' )
        else:
            flash( 'File uploaded and parsed successfully!', 'success' )

        # Remove the tmp file
        os.remove( tmp_file )

    return redirect( '/admin/manage' )


@admin_api.route( '/csv_download', methods=[ 'GET' ] )
def csv_download():
    '''
        csv_download

        Queries the database for ALL diseases and returns the results as a
        CSV to be edited. The CSV will be sorted by disease name.

        The format in which the csv will as follows:
        <disease id>, <disease name>, <finding 1>, <finding 2>, ...

        The findings will be formatted as such:
        <finding name>:<finding weight>

        Thus for example, the following could be outputted as a CSV:

        43ae01, Disease1, male:0.5, cough:1
        43ae02, Disease2, cough:0.25, elderly:0.50, fever:0.25

    '''

    # Query all the diseases
    diseases = Disease.query.ascending( Disease.name ).all()

    # Write it out to a CSV file
    directory = os.path.join( app.config[ 'UPLOAD_FOLDER' ], 'doknosis.csv' )
    csvWriter = csv.writer( open( directory, 'wb' ) )

    for disease in diseases:
        row = [ disease.mongo_id, disease.name ]

        for finding in disease.findings:
            row.append( '%s:%f' % ( finding.name, finding.weight ) )

        csvWriter.writerow( row )

    # Deliver the CSV file to the user
    return send_from_directory( app.config[ 'UPLOAD_FOLDER' ], 'doknosis.csv' )


@admin_api.route( '/manage', methods=[ 'GET' ] )
def manage_diseases():
    '''
        manage_diseases

        Gives an admin the option of downloading the CSV database and/or
        uploading a CSV database to update current one.
    '''
    return render_template( '/admin/manage.html' )


@admin_api.route( '/add/disease', methods=[ 'GET' ] )
def add_disease():
    '''
        add_diseases

        Adds a disease to the database ( if it doesn't already exist ).
        Redirects to the edit page with the new ( or existing ) disease.

        @param name - Disease name
    '''
    disease_name = request.args.get( 'name' ).strip().capitalize()

    # Query the database for the disease information
    disease = Disease.query.filter( {'name': disease_name} ).first()
    findings = []

    # Check to see if it already exists.
    if disease is None:
        disease = Disease( name=disease_name )
        disease.save()
    else:
        # If the diseases exists, create a findings list to show on the
        # edit page
        findings_list = disease.findings
        findings = [ x.to_dict() for x in findings_list ]

    return render_template( 'edit.html', disease=disease, findings=findings )


@admin_api.route( '/save/disease/<disease_id>' )
def save_disease( disease_id ):
    '''
        save_disease

        Create a disease if it doesn't already exist

        @param name - Disease name
    '''
    disease_name = request.args.get( 'name', None )
    if disease_name is None:
        return failure( 'Invalid Disease Name' )

    disease_name = disease_name.strip().capitalize()

    try:
        disease = Disease.query.filter(Disease.mongo_id == disease_id).first()
    except Exception:
        return failure( 'Invalid Disease ID' )

    if disease is None:
        return failure( 'Invalid Disease ID' )

    disease.name = disease_name
    disease.save()

    return success()


@admin_api.route( '/delete/disease/<disease_id>', methods=[ 'GET' ] )
def delete_disease( disease_id ):
    '''
        delete_disease

        Deletes a disease from the database

        @param disease_id - Disease MongoDB id
    '''
    try:
        disease = Disease.query.filter(Disease.mongo_id == disease_id).first()
    except Exception:
        # Invalid disease id, just send back to admin page.
        return redirect( '/admin' )

    if disease is not None:
        disease.remove()

    return redirect( '/admin' )


@admin_api.route( '/add/<disease_id>/finding', methods=[ 'POST' ] )
def add_finding( disease_id ):
    '''
        add_finding

        Add a finding ( name & weight ) to a disease

        @param disease_id   - Disease MongoDB id
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

    # Find the disease to add this finding too
    disease = Disease.query.filter( Disease.mongo_id == disease_id ).first()

    # Check our findings list to see if we have this finding already or not
    finding = Finding.query.filter( Finding.name == finding_name ).first()

    # Add this finding to the findings list
    if finding is None:
        finding = Finding( name=finding_name )
        finding.save()

    # Add this finding to the disease
    disease.findings.append(FindingWeight( name=finding_name, weight=weight ))
    disease.save()

    return success()


@admin_api.route( '/delete/<disease_id>/finding/', methods=[ 'POST' ] )
def delete_empty_finding( disease_id ):
    '''
        delete_empty_finding

        If for some reason a finding's name is empty ( by accident or in the
        CSV ) This method helps alleviate that corner case. Calls
        delete_finding with an empty finding_id

        @param disease_id - Disease MongoDB id
    '''
    return delete_finding( disease_id, '' )


@admin_api.route('/delete/<disease_id>/finding/<finding_id>', methods=['POST'])
def delete_finding( disease_id, finding_id ):
    '''
        delete_finding

        Deletes a finding from a disease instance

        @param disease_id - Disease MongoDB id
        @param finding_id - Finding id
    '''
    try:
        disease = Disease.query.filter(Disease.mongo_id == disease_id).first()
    except Exception:
        return failure( 'Invalid Disease ID' )

    # Find finding and remove it
    for find in disease.findings:
        if find.name == finding_id:
            disease.findings.remove( find )
            break
    disease.save()

    # Also check if this finding no longer exists in the db.
    count = Disease.query.filter({'findings.name': finding_id}).count()
    if count == 0:
        # Remove from findings list
        finding = Finding.query.filter( Finding.name == finding_id ).first()
        finding.remove()

    return success()


@admin_api.route( '/edit/<disease_id>')
def edit_disease( disease_id ):
    '''
        edit_disease

        Queries a disease by its MongoDB id and returns the edit page for that
        disease.

        @param disease_id - Disease MongoDB id
    '''
    disease = Disease.query.filter( Disease.mongo_id == disease_id ).first()
    findings = [ x.to_dict() for x in disease.findings ]

    return render_template( 'edit.html', disease=disease, findings=findings )
