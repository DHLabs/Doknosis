import json

from flask import Blueprint, request, render_template, redirect, url_for

from server.cache import cache
from server.db import db, Finding, Disease, FindingWeight
from sqlalchemy import func
admin_api = Blueprint( 'admin_api', __name__ )

@admin_api.route( '/' )
def admin_index():
    '''
        admin_index

        Returns the 10 latest diseases entered into the database
    '''
    diseases = Disease.query.limit( 10 ).descending( Disease.mongo_id ).all()
    return render_template( 'admin.html', random_diseases=diseases )

@admin_api.route( '/add/disease', methods=[ 'GET' ] )
def add_disease():
    '''
        add_diseases

        Adds a disease to the database ( if it doesn't already exist ).
        Redirects to the edit page with the new ( or existing ) disease.

        @param name - Disease name
    '''
    disease_name = request.args.get( 'name' )

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
    disease_name = request.args.get( 'name' )
    disease = Disease.query.filter( Disease.mongo_id == disease_id ).first()

    if disease is not None:
        disease.name = disease_name
        disease.save()
    
    return json.dumps({})

@admin_api.route( '/delete/disease/<disease_id>', methods=[ 'GET' ] )
def delete_disease( disease_id ):
    '''
        delete_disease

        Deletes a disease from the database

        @param disease_id - Disease MongoDB id
    '''
    disease = Disease.query.filter( Disease.mongo_id == disease_id ).first()
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
    finding_name = request.form[ 'name' ]
    weight       = float( request.form[ 'weight' ] )

    disease = Disease.query.filter( Disease.mongo_id == disease_id ).first()
    finding = Finding.query.filter( Finding.name == finding_name ).first()

    if finding is None:
        finding = Finding( name=finding_name )
        finding.save()
    
    disease.findings.append( FindingWeight( name=finding_name, weight=weight ) )
    disease.save()

    return json.dumps({})

@admin_api.route( '/delete/<disease_id>/finding/', methods=[ 'POST' ] )
def delete_empty_finding( disease_id ):
    '''
        delete_empty_finding

        If for some reason a finding's name is empty ( by accident or in the CSV )
        This method helps alleviate that corner case. Calls delete_finding with 
        an empty finding_id

        @param disease_id - Disease MongoDB id
    '''
    return delete_finding( disease_id, '' )

@admin_api.route( '/delete/<disease_id>/finding/<finding_id>', methods=[ 'POST' ] )
def delete_finding( disease_id, finding_id ):
    '''
        delete_finding

        Deletes a finding from a disease instance

        @param disease_id - Disease MongoDB id
        @param finding_id - Finding id
    '''
    disease = Disease.query.filter( Disease.mongo_id==disease_id ).first()

    # Find finding and remove it
    for find in disease.findings:
        if find.name == finding_id:
            disease.findings.remove( find )
            break

    disease.save()
    return json.dumps( {} )    

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

@admin_api.route( '/disease/autocomplete', methods=['GET'] )
def finding_autocomplete():
    '''
        finding_autocomplete

        Handles autocomplete queries for finding names

        @param term - Substring of finding name we're searching for.
    '''
    term = request.args.get( 'term' )

    diseases = Disease.query.filter( { 'name': { '$regex': '.*%s.*' % ( term ) } } )\
                    .limit( 20 )\
                    .ascending( Disease.name )\
                    .all()

    # Convert into an JSON object
    json_findings = []
    for finding in diseases:
        json_findings.append( { 'id':    str( finding.mongo_id ),\
                                'label': finding.name,\
                                'value': finding.name } )
    return json.dumps( json_findings )
    