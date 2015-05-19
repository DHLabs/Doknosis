import csv,os,time,json

from flask import Blueprint, request, render_template, redirect, flash
from flask import send_from_directory
from flask import current_app as app

from server.constants import EXPLANATION_TYPE_IDENTIFIERS
from server.db import Finding, Explanation,DBError
from server.helpers import success, failure
from server.helpers.data import parse_prevalence_csv,parse_gdata
from server.helpers.GDataClient import GDataClient,GDError,GDATA_MAIN_DOC,GDATA_WS_PREVALENCE,GDATA_WS_GEO
from werkzeug import secure_filename

admin_api = Blueprint( 'admin_api', __name__ )

BROWSER_ITEMS_PER_PAGE=10

def allowed_file( filename ):
    return '.' in filename and \
        filename.rsplit( '.', 1 )[1] in app.config[ 'ALLOWED_EXTENSIONS' ]


@admin_api.route( '/' )
def admin_index():
    '''
        admin_index

        Current page of Explanation browser.
    '''

    page = int( request.args.get( 'page', 1 ) )

    curpage = Explanation.query.ascending( Explanation.name ).paginate( page=page,per_page=BROWSER_ITEMS_PER_PAGE )

    return render_template( '/admin/browse.html', pagination=curpage )

@admin_api.route( '/jumpto/explanation' )
def admin_jumpto():
    '''
        Jump to a different page of the browser.
    '''

    
    initial_page = int( request.args.get( 'page', 1 ) )
    seeking_name = request.args.get( 'name', None )
    if seeking_name is None:
        return failure( 'No name specified!' )

    # There is probably a faster way...
    curpage = Explanation.query.ascending( Explanation.name ).paginate( page=1, per_page=BROWSER_ITEMS_PER_PAGE )

    # flash('Seeking {}'.format(seeking_name),'error')

    exp_found = next((True for exp in curpage.items if exp.name == seeking_name), False)
    while(exp_found == False and curpage.has_next()):
        # if exp_found == False:
        #     flash('Not found on page {}'.format(curpage.page),'error')
        curpage = curpage.next(error_out=True)
        # flash('All names on page = {}'.format([exp.name for exp in curpage.items]),'error')
        exp_found = next((True for exp in curpage.items if exp.name == seeking_name), False)
        # if exp_found == True:
        #     flash('Found on page {}'.format(curpage.page),'error')

    if exp_found == False:
        flash('Failed to find explanation with name {} in database!'.format(seeking_name),'error')
        while(curpage.page > initial_page and curpage.has_prev()):
            curpage = curpage.prev(error_out=True)

    return render_template( '/admin/browse.html', pagination=curpage )


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
        t1 = time.time()

        filename = secure_filename( 'tmp.csv' )
        tmp_file = os.path.join( app.config[ 'UPLOAD_FOLDER' ], filename )
        file.save( tmp_file )

        # Now process the sucker!
        errors,update_explanations = parse_prevalence_csv( tmp_file )

        # Here we do the actual database updating.
        Explanation.bulk_upsert(update_explanations.values())
        upload_time = ( time.time() - t1 )
        if len(errors):
            print errors

        if len( errors ) > 0:
            flash('The following errors encountered parsing file (processing took {} seconds).'.format(upload_time),'error')
            for err in errors:
                flash(err,'error')
        else:
            flash( 'File uploaded and parsed successfully (processing took {} seconds)!'.format(upload_time), 'success' )

        # Remove the tmp file
        os.remove( tmp_file )

    return redirect( '/admin/manage' )


@admin_api.route( '/gdata_sync', methods=[ 'POST' ] )
def gdata_sync():
    '''
        gdata_sync

        Sync data directly from google sheets.  A direct access username and password must be passed in.
    '''
    if request.method != 'POST':
        return redirect( '/admin/manage' )

    t1 = time.time()

    username = request.form['username']
    pswd = request.form['password']

    gds = GDataClient(username,pswd)

    gds.set_document(GDATA_MAIN_DOC)

    gds.set_worksheet(GDATA_WS_PREVALENCE)
    gd_prev,err = gds.read_to_dict('explanatoryvariable')
    if err is not None:
        flash(err,'error')
        return redirect( '/admin/manage')
    
    gds.set_worksheet(GDATA_WS_GEO)
    gd_geo,err = gds.read_to_dict('explanatoryvariable')
    if err is not None:
        flash(err,'error')
        return redirect( '/admin/manage')

    errors,update_explanations = parse_gdata(gd_prev,gd_geo)

    update_time = ( time.time() - t1 )

    if len( errors ) > 0:
        flash('The following errors encountered parsing google sheet'
              '(took {} seconds).  Errors logged to "sync_errors.log".'
              .format(update_time),'error')
        for err in errors[0:100]:
            flash(err,'error')
        if len(errors) > 100:
            flash('Only printing the first 100 out of {} errors.'.format(len(errors)),'error')
        with open('sync_errors.log','w') as fh:
            fh.write('The following errors encountered parsing google sheet.\n')
            for err in errors:
                fh.write(err+'\n')

    else:
        Explanation.remove_all()
        Finding.remove_all()
        Explanation.bulk_upsert(update_explanations.values())
        flash( 'Google sheet parsed successfully (processing took {} seconds)!  Database reloaded.'.format(update_time), 'success' )

    return redirect( '/admin/manage' )


@admin_api.route( '/csv_download', methods=[ 'GET' ] )
def csv_download():
    '''
        csv_download

        Queries the database for ALL explanations and returns the results as a
        CSV to be edited. The CSV will be sorted by explanation name, formatted as:
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

        Triggered from explanation browser.  Adds a explanation to the database ( if it doesn't already exist ).
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
    explanation = Explanation.query.filter( Explanation.name==explanation_name ).limit(1).first()
    findings = []

    # Check to see if it already exists.
    if explanation is None:
        explanation = Explanation( name=explanation_name, type_identifier=explanation_type_id )
    else:
        if explanation.type_identifier != explanation_type_id:
            return failure('Explanation with name {} already exists, but type in database is {}, not {}!'.format(explanation_name,
                                                                                                                 explanation.type_identifier,
                                                                                                                 explanation_type_id))

    return render_template( 'edit.html', explanation=explanation )


@admin_api.route( '/save/explanation/' )
@admin_api.route( '/save/explanation/<explanation_id>' )
def save_explanation( explanation_id=None ):
    '''
        save_explanation

        Create a explanation if it doesn't already exist, save all the changes currently pending
        on the edit page to the database.

        @param name - Explanation name
    '''

    explanation_name = request.args.get( 'name', None )
    if explanation_name is None:
        return failure( 'No Explanation Name' )

    explanation_name = explanation_name.strip().capitalize()

    explanation_type_id = request.args.get( 'type_identifier', None )
    if explanation_type_id is None:
        return failure( 'No Explanation Type' )

    findings = json.loads(request.args.get( 'findings', None ))

    try:
        Explanation.upsert(name=explanation_name, type_identifier=explanation_type_id, finding_dicts=findings, mongo_id=explanation_id )
    except Exception as err:
        return failure('Upsert failure (type {}): {}'.format(err.__class__.__name__, err))

    return success()


@admin_api.route( '/delete/explanation/', methods=[ 'GET' ] )
@admin_api.route( '/delete/explanation/<explanation_id>', methods=[ 'GET' ] )
def delete_explanation( explanation_id=None ):
    '''
        delete_explanation

        Deletes a explanation from the database (if it's been saved) and returns us to the browsing page

        @param explanation_id - Explanation MongoDB id
    '''
    Explanation.delete(explanation_id)

    return redirect( '/admin' )


@admin_api.route( '/add/<explanation_id>/finding', methods=[ 'POST' ] )
def add_finding( explanation_id ):
    '''
        add_finding

        Check the finding before adding it to the table in the edit page.  
        NOTE: finding not added to database until edit page is saved!

        @param explanation_id   - Explanation MongoDB id
        @param name         - Finding name
        @param weight       - Finding weight
    '''
    finding_name = request.form.get( 'name', None )

    if finding_name is None:
        return failure('Invalid Finding Name')

    finding_name = finding_name.strip().lower()
    try:
        weight       = float( request.form[ 'weight' ] )
    except ValueError:
        return failure('Invalid Finding Weight')

    return success()

@admin_api.route( '/edit/<explanation_id>')
def edit_explanation( explanation_id ):
    '''
        edit_explanation

        Queries a explanation by its MongoDB id and returns the edit page for that
        explanation.

        @param explanation_id - Explanation MongoDB id
    '''
    explanation = Explanation.query.filter( Explanation.mongo_id == explanation_id ).limit(1).first()

    return render_template( 'edit.html', explanation=explanation )


# @admin_api.route( '/delete_all', methods=[ 'GET' ])
def delete_all():
    '''
        Clear out the entire database.

        Get rid of this?

    '''
    
    Explanation.remove_all()
    Finding.remove_all()

    flash('Database deleted','delete')

    return redirect( '/admin/manage' )
