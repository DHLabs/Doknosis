import json

from flask import Blueprint, request, render_template, redirect, url_for

from server.cache import cache
from server.db import db, Finding, Disease, DiseaseFindings
from sqlalchemy import func
admin_api = Blueprint( 'admin_api', __name__ )

@admin_api.route( '/' )
def admin_index():
    diseases = Disease.query.order_by( func.rand() ).limit(10).all()
    return render_template( 'admin.html', random_diseases=diseases )

@admin_api.route( '/add/disease', methods=[ 'GET' ] )
def add_disease():
    disease_name = request.args.get( 'name' )

    disease = Disease.query.filter( Disease.name == disease_name ).first()
    findings = []

    if disease is None:
        disease = Disease( name=disease_name )
        db.session.add( disease )
        db.session.commit()
    else:
        findings = disease.findings
        fids = {}
        for find in findings:
            fids[ find.finding_id ] = ( find.id, find.weight )

        finding_names = Finding.query.filter( Finding.id.in_( fids.keys() ) ).all()
        findings = []
        for find in finding_names:
            data = fids[ find.id ]
            fobj = {}
            fobj[ 'id' ] = data[0]
            fobj[ 'name' ] = find.name
            fobj[ 'weight' ] = data[1]
            findings.append( fobj )

    return render_template( 'edit.html', disease=disease, findings=findings )

@admin_api.route( '/save/disease/<int:disease_id>' )
def save_disease( disease_id ):
    disease_name = request.args.get( 'name' )
    disease = Disease.query.filter( Disease.id == disease_id ).first()

    if disease is not None:
        disease.name = disease_name
        db.session.commit()
    
    return json.dumps({})

@admin_api.route( '/delete/disease/<int:disease_id>', methods=[ 'GET' ] )
def delete_disease( disease_id ):
    disease = Disease.query.filter( Disease.id == disease_id ).first()
    if disease is not None:
        db.session.delete( disease )
        db.session.commit()
    return redirect( '/admin' )

@admin_api.route( '/add/<int:disease_id>/finding', methods=[ 'POST' ] )
def add_finding( disease_id ):
    finding_name = request.form[ 'name' ]
    weight       = float( request.form[ 'weight' ] )

    disease = Disease.query.filter( Disease.id == disease_id ).first()

    finding = Finding.query.filter( Finding.name == finding_name ).first()
    if finding is None:
        finding = Finding( name=finding_name )
    
    db.session.add( finding )

    association = DiseaseFindings( weight=weight )
    association.finding = finding
    disease.findings.append( association )
    db.session.flush()    
    db.session.commit()

    return json.dumps( {'id': association.id} )

@admin_api.route( '/delete/finding/<int:finding_id>', methods=[ 'POST' ] )
def delete_finding( finding_id ):
    finding = DiseaseFindings.query.filter( DiseaseFindings.id == finding_id ).first()
    db.session.delete( finding )
    db.session.commit()

    return json.dumps( {} )    

@admin_api.route( '/edit/<int:disease_id>')
def edit_disease( disease_id ):
    disease = Disease.query.filter( Disease.id == disease_id ).first()
    findings = disease.findings

    fids = {}
    for find in findings:
        fids[ find.finding_id ] = ( find.id, find.weight )

    finding_names = Finding.query.filter( Finding.id.in_( fids.keys() ) ).all()
    findings = []
    for find in finding_names:
        data = fids[ find.id ]
        fobj = {}
        fobj[ 'id' ] = data[0]
        fobj[ 'name' ] = find.name
        fobj[ 'weight' ] = data[1]
        findings.append( fobj )

    return render_template( 'edit.html', disease=disease, findings=findings )

@admin_api.route( '/disease/autocomplete', methods=['GET'] )
def finding_autocomplete():
    term = request.args.get( 'term' )

    findings = Disease.query.filter( Disease.name.contains( term ) ).limit( 10 )

    # Convert into an JSON object
    json_findings = []
    for finding in findings:
        info = {}
        info[ 'id' ]    = finding.id
        info[ 'label' ] = finding.name
        info[ 'value' ] = finding.name
        
        json_findings.append( info )
    
    return json.dumps( json_findings )    