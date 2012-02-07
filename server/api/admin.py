import json

from flask import Blueprint, request, render_template, redirect, url_for

from server.cache import cache
from server.db import db, Finding, Disease, FindingWeight
from sqlalchemy import func
admin_api = Blueprint( 'admin_api', __name__ )

@admin_api.route( '/' )
def admin_index():
    diseases = Disease.query.limit( 10 ).descending( Disease.mongo_id ).all()
    return render_template( 'admin.html', random_diseases=diseases )

@admin_api.route( '/add/disease', methods=[ 'GET' ] )
def add_disease():
    disease_name = request.args.get( 'name' )

    disease = Disease.query.filter( {'name': disease_name} ).first()
    findings = []

    if disease is None:
        disease = Disease( name=disease_name )
        disease.save()
    else:
        findings_list = disease.findings
        findings = [ x.to_dict() for x in findings_list ]

    return render_template( 'edit.html', disease=disease, findings=findings )

@admin_api.route( '/save/disease/<disease_id>' )
def save_disease( disease_id ):
    disease_name = request.args.get( 'name' )
    disease = Disease.query.filter( Disease.mongo_id == disease_id ).first()

    if disease is not None:
        disease.name = disease_name
        disease.save()
    
    return json.dumps({})

@admin_api.route( '/delete/disease/<disease_id>', methods=[ 'GET' ] )
def delete_disease( disease_id ):
    disease = Disease.query.filter( Disease.mongo_id == disease_id ).first()
    if disease is not None:
        disease.remove()

    return redirect( '/admin' )

@admin_api.route( '/add/<disease_id>/finding', methods=[ 'POST' ] )
def add_finding( disease_id ):
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

@admin_api.route( '/delete/<disease_id>/finding/<finding_id>', methods=[ 'POST' ] )
def delete_finding( disease_id, finding_id ):
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
    disease = Disease.query.filter( Disease.mongo_id == disease_id ).first()
    findings = [ x.to_dict() for x in disease.findings ]

    return render_template( 'edit.html', disease=disease, findings=findings )

@admin_api.route( '/disease/autocomplete', methods=['GET'] )
def finding_autocomplete():
    term = request.args.get( 'term' )

    diseases = Disease.query.filter( { 'name': { '$regex': '.*%s.*' % ( term ) } } ).limit( 10 ).ascending( Disease.name ).all()

    # Convert into an JSON object
    json_findings = []
    for finding in diseases:
        info = {}
        info[ 'id' ]    = str( finding.mongo_id )
        info[ 'label' ] = finding.name
        info[ 'value' ] = finding.name
        
        json_findings.append( info )
    
    return json.dumps( json_findings )    