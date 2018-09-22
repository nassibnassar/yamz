This is the README for the YAMZ metadictionary and includes instructions for 
deploying on a local machine (via [Docker Compose](https://docs.docker.com/compose/)) 
for testing and on [Heroku](https://www.heroku.com) for a 
scalable production version. These assume a Ubuntu GNU/Linux environment, but 
should be easily adaptable to any system; YAMZ is written in Python and uses 
only cross-platform packages.  This file is formatted by hand and does not
contain markdown.
  
  Originally authored by Chris Patton. Last updated 10th September 2018 (lewismc). 

YAMZ is formerly known as SeaIce; for this reason, the database tables 
and API use names based on "SeaIce". 

Contents 
========
 
 1. Configuring and Deploying a Local Instance
     1.1 OAuth credentials and app key
     1.2 N2T persistent identifier resolver credentials
     1.3 Test the instance
 
 2. Deploying to Heroku
     2.1 Prerequisites - Create the deploy_keys branch
     2.2 Heroku-Postgres
     2.3 Mailgun
     2.4 Heroku-Scheduler
     2.5 Making changes
     2.6 Exporting the dictionary

 3. URL Forwarding

 4. Building the Documentation 

 5. Deprecated Local Installation Instructions
     5.1 Prerequisites
     5.2 Postgres authentication
     5.3 Create the database
     5.4 Create a role for standard queries
     5.5 OAuth credentials and app key
     5.6 N2T persistent identifier resolver credentials
     5.7 Test the instance

The contents of this directory are as follows: 

  sea.py . . . . . . . . . . Console utility for scoring and classifying
                             terms and other things. 

  ice.py . . . . . . . . . . Web server front end.

  digest.py  . . . . . . . . Console email notification utility.

  requirements.txt . . . . . Heroku package dependencies.

  Procfile . . . . . . . . . Heroku configuration.

  seaice/  . . . . . . . . . The SeaIce Python module. 

  html/  . . . . . . . . . . HTML templates, static Javascript and CSS, 
                             including bootstrap.js. 
 
  doc/ . . . . . . . . . . . API documentation and tools for building it. 

  .seaice/.seaic_auth  . . . DB credentials, API keys, app key, etc. Note 
  .seaice/.seaice_auth  . . . DB credentials, API keys, app key, etc. Note 
                             that these files are just templates and don't
                             contain actual keys. 

  docker/ . . . . . . . . .  Docker files for various components and service composition

Previously, users were required to download a variety of software dependencies in order to
run YAMZ. This is not longer required as the build and deployment is managed via the popular
[Docker Compose](https://docs.docker.com/compose/) technology making life much easier.
Basically, just ensure that you have Docker and Docker Compose installed.

# 1. Configuring and Deploying a Local Instance with Docker Compose

## 1.1 OAuth credentials and app key

YAMZ uses Google for third party authentication (OAuth-2.0) management of 
logins. Visit https://console.developers.google.com to set this service up 
for your instance.
 * Navigate to something like __API's and Services -> Credentials__.
 * From the blue dropdown 'Create credentials' menu, select 'OAuth client ID'.
 * You will be required to navigate to the __OAuth consent screen__ where you
 should set the following parameter values
 
 - Product name shown to users  . . . . YAMZ-Dev
 - Product Website  . . . . . . . . . . http://localhost:5000

If at this stage you have more information available, you are free to populate more 
fields. However, eventually you will want to save. This will then prompt you to enter
the following information.

 - Application type . . . . . . . . . . Web application
 - Name . . . . . . . . . . . . . . . . YAMZ-Dev
 - Authorized JavaScript origins  . . . http://localhost:5000 
 - Authorized redirect URI  . . . . . . http://localhost:5000/authorized 

Create another set of credentials for your heroku instance, say yamz-dev:

 Application type . . . . . . . . . . Web application
 Authorized javascript origins  . . . http://yamz-dev.herokuapp.com
 Authorized redirect URI  . . . . . . http://yamz-dev.herokuapp.com/authorized 

In each case, you should obtain a pair of values to put into another
configuration file called '.seaice_auth'. Create or edit this file,
replacing google_client_id with the returned 'Client ID' and replacing
google_client_secret with the returned 'Client secret'.

xxx Where does app_secret come in? does it come from the 'API key'?
    Manoj: app_secret only needed for heroku deployment

(See section 2.) XXX Are the instructions there complete, eg, redirect URL?) 
XXX ?document this in a 0.x section, since it applies to local and heroku?

Next, create a configuration file called '.seaice_auth' with the appropriate 
client IDs and secret keys. For instance, you may have credentials for 
'http://localhost:5000', as well as a deployment on heroku: 

XXX the google_client_id identifies your client software/(app?) and is
    paired with the redirect URL, eg, one for 'http://localhost:5000'
    and another for http://yamz.net...
xxx is this correct? each unique post-auth redirection target needs its
    own unique google_client_id
XXX to do: allow local dev to take place offline, ie, without contact
     with google for Auth or with minters and binders and n2t
xxx to do: let people create test terms that expire in two weeks

  [dev]
  google_client_id = 000-fella.apps.googleusercontent.com
  google_client_secret = SECRET1
  app_secret = SECRET2

  [heroku]
  google_client_id = 000-guy.apps.googleusercontent.com
  google_client_secret = SECRET3
  app_secret = SECRET4

IMPORTANT NOTE: A template of this file is provided in the github
repository. This file should remain secret and must not be published. 
We provide the template, since heroku requires a committed file. 

For convenience, this file will also keep the Flask app's secret key. For 
this key, enter a long, random string of characters. Finally, set the correct 
file permissions with: 

  $ chmod 600 .seaice_auth


## 1.2 N2T persistent identifier resolver credentials

Whenever a new term is created, YAMZ uses an API to n2t.net (maintained by
the California Digital Library) in order to generate ("mint") a persistent
identifier.  The main role of n2t.net is to be a resolver for the public-
facing URLs that persistently identify YAMZ terms.  It is necessary to
provide a minter password for API access to this web service.  To do so
include a line in ".seaice_auth" for every view:
 
   minter_password = PASS

A password found in the MINTER_PASSWORD environment variable, however, will
be preferred over the file setting.  This password is used again in the
API call to store metadata in a YAMZ binder on n2t.net.  The main bit of
metadata stored is the redirection target URL that supports resolution of
ARK identifiers for YAMZ terms.

Because real identifiers are meant to be persistent, no local or test
instance of YAMZ should ever set the boolean "prod_mode" parameter in
".seaice_auth".  For such instances the generated and updated terms
should just be for identifiers meant to be thrown away.  Only on the
real production instance of YAMZ, when you're done testing term creation
and update, should it be set to "enable" (the default is don't enable).


## 1.3 Test the instance

Simply build the software orchestration
```
$ docker-compose build
```
This may take quite a while and will produce a lot of output to std out.
Once it has completed however, you are ready to deploy the local YAMZ
software stack.
```
$ docker-compose up
```
If all goes well, you should be able to navigate to your server by typing 
'http://localhost:5000' in the address bar. To verify that you've set up 
Google OAuth-2.0 correctly, try logging in. This will create an account.
Try adding a new term, modifying and deleting a term, and commenting on 
terms.

# 2. Deploying to Heroku

The YAMZ prototype is currently hosted at http://yamz.herokuapp.com. 
Heroku is a cloud-computing service which allows users to host web-based
software projects. Heroku is scalable for a price; however, we can 
still achieve quite a bit without spending money. We have access to a 
small Postgres database, can schedule jobs, use a variety of packages 
(all we need are available), and deploy easily with Git. Some limitations
of Heroku are that it is impossible to set up DB roles and any local files
cannot be assumed to persist after a reboot.

To begin, you need to setup an account with Heroku and download their software. 
(It's nothing major, just some tools for running commands, interacting with 
the database, etc.) Visit http://www.heroku.com. 

Heroku requires a couple additional configuration files and some small
code changes. The additional files (already set up in the repo) are:

  Procfile . . . . . . . specifies the commands that start web server, as 
                         well as periodic jobs. 

  requirements.txt . . . a list of packages required by our software that 
                         Heroku needs to make available. These are 
                         available via pip.

I used the following tutorial: https://devcenter.heroku.com/articles/python
to set these up.  Once you've set up your heroku account, you're ready to
deploy. 

The recommended best practice for managing your heroku instance is to set up
a local branch called 'deploy_keys' based on 'master'. In this branch, edit 
.seaice and .seaice_auth to contain actual passwords and API and app keys.
NOTE: IT IS CRITICAL THAT YOU DON'T PUSH THIS BRANCH TO GITHUB.
Publishing these secrets compromises the security of the entire app.

Login via the heroku website and create a new app. Let's say we've named it
"fella". Navigate to the directory containing the cloned repository. Create
and checkout the branch 'deploy_keys'. 

  $ git checkout -b deploy_keys
  $ heroku login
  $ heroku git:remote -a fella

This creates a "slug" containing our code and its dependencies. To get the web 
app running, we'll now need to set up a database and a couple of heroku backend 
services. 


## 2.1 Heroku-Postgres

Heroku-Postgres is a scalable DB interface for heroku apps. (See the
python section of devcenter.heroku.com/articles/heroku-postgresql .)
To create a free addon,

  $ heroku addons:create heroku-postgresql:hobby-dev

The 'master' branch is set up to use either a local postgres database server
or Heroku-Postgres.  The location of the DB in the "cloud" is specified
when you create the heroku addon, and heroku automatically sets the
instance's environment variable DATABASE_URL, which you can query with

  $ heroku config

Using 'sea' or 'ice' with '--config=heroku' will force SeaIce to use the
web address found in this variable to connect to the DB. (Note this is the
default.) Heroku-Postgres doesn't allow you to create roles, so '--role'
will be ignored and the default will be used.  To create the database schema: 

  $ heroku run python sea.py --init-db


## 2.2 Mailgun

YAMZ provides an email notification service for users who opt in. A utility 
called 'digest' collects for each user all notifications that haven't
previously been emailed into a single digest. The code uses a heroku backend
app called Mailgun for SMTP service. To set this up, simply type (you may be
asked to verify your heroku account with a credit card, but note your card
should not be charged for the most basic service level)

  $ heroku addons:create mailgun

This sets a number of instance environment variables (see "heroku config").
Of them the code uses "MAILGUN_SMTP_LOGIN" and "MAILGUN_SMTP_PASSWORD" to
connect to Mailgun. Normally that happens when notifications are harvested
by the scheduler (below), but to send out notifications manually, type: 

  $ heroku run python digest.py 


## 2.3 Heroku-Scheduler

There are two periodic jobs that need to be scheduled in YAMZ: the term 
classifier and the email digest. To set this up, do: 
  
  $ heroku addons:create scheduler
  $ heroku addons:open scheduler

The second command will take you to the web interface for the scheduler. Add
the following two jobs: 

  "python sea.py --classify-terms" . . . . . every 10 minutes
  "python digest.py" . . . . . . . . . . . . once per day


## 2.4 Starting the instance

Now that your instance is all prepared, you can get it up and running with

  $ git push heroku deploy_keys:master

This pushes the secret keys found in the local deploy_keys branch so that
they update the remote master branch on heroku.  (xxx see section 1.4 and
??? for setting the secrets)
 xxx app_secret is the (api key?) password from netrc, or "heroku auth:token"?


## 2.5 Making changes

Deploying changes to heroku is made easy with Git. Suppose we have changes
to 'master' that we want to push to heroku.

  $ git checkout deploy_keys
  $ git merge master          # updates deploy_keys with latest master commits
  $ git push heroku deploy_keys:master

The first command checks out the already created local 'deploy_keys' branch.
The second command merges the latest commits from the master branch into it,
and the final command updates the heroku master branch, which also restarts
the instance.  This keeps the secrets outside the master branch.

When you next checkout the master branch, however, your keys and secrets in
the .seaice* files will be overwritten, so you may want to save them in
separate files that you can copy back in to the branch when you later deploy
again; just make sure those separate files don't ever become part of any
branch that will show up in the public github repo.


## 2.6 Exporting the dictionary

The SeaIce API includes queries for importing and exporting database tables 
in JSON formatted objects. This could be used to backup the entire database.
Note however that imports must be done in the proper order in order to satisfy
foreign key constraints. To back up the dictionary, do: 

  $ heroku config | grep DATABASE_URL
  DATABASE_URL: <whatever>
  $ export DATABASE_URL=<whatever> 
  $ ./sea.py --config=heroku --export=Terms >terms.json


# 3. URL forwarding

The current stable implementation of YAMZ is redirected from http://yamz.net. 
Setting this up takes a bit of doing. The following instructions are synthsized
from http://lifesforlearning.com/heroku-with-godaddy/ for redirecting a domain
name managed by GoDaddy to a Heroku app.

Launch the "Domains" app on GoDaddy. Under "Forward Domain" for the appropriate
domain (let's call it "fella.org"), add the following settings:
 
 Forward to . . . . . . . . . . . . . . . . . . . . http://www.fella.org
 Redirect type  . . . . . . . . . . . . . . . . . . 301 (Permanent)
 Forward settings . . . . . . . . . . . . . . . . . Forward only 
 Update nameservers and DNS settings 
           to support this change . . . . . . . . . yes

Next, under "Manage DNS", remove all entries except for 'A (Host)' and 'NS 
(Nameserver)', and add the following under 'CName (Alias)': 

 Record type  . . . . . . . . . . . . . . . . . CNAME (Alias)
 Host . . . . . . . . . . . . . . . . . . . . . www
 Points to  . . . . . . . . . . . . . . . . . . http://fella.herokuapp.com
 TTL  . . . . . . . . . . . . . . . . . . . . . 1 Hour

Next, change the IP address for entry '@' under 'A (Host)' to 50.63.202.31
(the current IP address of yamz.net).

That's it for DNS configuration. The last thing we need to do is modify the 
redirect URLs in the Google OAuth API. Edit the authorized javascript origins 
and redirect URI by replacing "fella.herokuapp.com" with "fella.org" and 
save. 

It can take a couple hours to a day for your DNS settings to propogate. Once 
it's done, you can navigate to YAMZ by typing "fella.org" into your browser.
Try logging in to verify that the OAuth settings are also correct. 


# 4. Building the Project Documentation

The seaice package (but not this README file) is autodoc'ed using
python-sphinx. To install on Ubuntu:

  $ sudo apt-get install python-sphinx

The directory doc/sphinx includes a Makefile for exporting the docs to 
various media. For example, 

  make html
  make latex

# 5. Deprecated Local Installation Instruction

## 5.1 Prerequisites

Before you get started, you need to set up a database and some software 
packages.  On Mac OS X, this may suffice:

  $ pip install psycopg2 Flask configparser flask-login flask-OAuth \
      python-dateutil

On Ubuntu, grab the following:
  
  python-flask . . . . . . . Simple HTTP server.

  postgresql . . . . . . . . We're using PostgreSQL for database managment. 

  python-psycopg2  . . . . . Python API for PostgreSQL.

  python-pip . . . . . . . . Package manager for additional Python 
                             programs. 

and then download a package from pip that handles configuration files nicely:

  $ sudo pip install \
      configparser flask-login flask-OAuth python-dateutil urlparse

To start, we'll set up a database in postgres. First, we need to do some 
configuration. Postgres requires an administrative user called 'postgres'. 
It may be a good idea to create a SeaIce user (called "role" in postgres 
jargon) with read/write access granted on the tables.  This work takes
place in the top-level source directory.  On Linux (assuming postgres was
installed using sudo), set postgres' password: 
```
  $ sudo -u postgres psql template1
  template1=# alter user postgres with encrypted password 'PASS';  
  template1=# \q [quit] 
```
On a Mac, assuming homebrew installed the software in your home directory
(ie, without sudo), you'll need to initialize postgres first, with
something like these commands:
```
  $ initdb /usr/local/var/postgres
  $ cp /usr/local/Cellar/postgresql/9.6.3/homebrew.mxcl.postgresql.plist \
       ~/Library/LaunchAgents/
  $ launchctl load -w ~/Library/LaunchAgents/homebrew.mxcl.postgresql.plist
```
That makes postgres run automatically after a reboot. Create user 'postgres'
and set the password to 'PASS':

  $ createuser -d postgres
  $ createuser -d SeaIce
  $ psql -U postgres -c "alter user postgres with encrypted password 'PASS'"


## 5.2 Postgres authentication

Now configure the authentication method for postgres and all other users 
connecting locally. In /etc/postgresql/9.1/main/pg_hba.conf (on our Mac,
/usr/local/var/postgres/pg_hba.conf), change "peer" in the line that will
become (xxx shouldn't the md5 show below?)

  local   all         postgres                          peer

to "md5" for the administrative account and local unix domain socket 
connections. Next, we want to only be able to connect to the database from 
the local machine. In /etc/postgresql/9.1/main/postgresql.conf (on our Mac,
/usr/local/var/postgres/postgresql.conf), uncomment the line

  listen_addresses = 'localhost'

After you've done this, you need to restart the postgres server. On Linux,

  $ sudo service postgresql restart

or on our homebrew-based Mac,

  $ launchctl stop  ~/Library/LaunchAgents/homebrew.mxcl.postgresql.plist
  $ launchctl start ~/Library/LaunchAgents/homebrew.mxcl.postgresql.plist


## 5.3 Create the database

Finally, log back in to postgres to create the database,

  $ sudo -u postgres psql
  postgres=# create database seaice with owner postgres;

or on our Mac,

  $ psql -U postgres -c 'create database seaice with owner postgres'
  
(Using unique, completely random passwords is a good idea here.) Next, 
create a configuration file for the database and user account you set up. 
Create a file called '.seaice' like: 

  [default]
  dbname = seaice
  user = postgres
  password = PASS
xxx do this in a separate "local_deploy" dir?
xxx user = reader?
xxx separate section for [contributor] ? eg
xxx [contributor]
xxx dbname = seaice
xxx user = contributor
xxx password = PASSWORD3

IMPORTANT NOTE: A template of this file is provided in the github
repository. Your working version of this file should remain secret
and must not be published.  Set the correct file permissions with: 

  $ chmod 600 .seaice

This file is used by the SeaIce DB connector to grant access to the database.
To initialize the DB schema and tables, type:
  
  $ ./sea.py --init-db --config=.seaice
  $ ./sea.py --init-db --config=local_deploy/.seaice


xxx move this section above preceding, since you may need those roles?

## 5.4 Create a role for standard queries

At this point, it's suggested that you set up user standard read/write 
permissions on the table (no DROP, CREATE, GRANT, etc.) for most of the 
database queries. Note that this isn't applicable in Heroku; the postgres
interface there doesn't allow you to control user views. 
  
  postgres=# create user contributor with encrypted password 'PASS';
  postgres=# \c seaice;
  postgres=# grant usage on schema SI, SI_Notify to contributor;
  postgres=# grant select, insert, update, delete on all tables in 
             schema SI, SI_Notify to contributor;

On our Mac, that would be

  $ psql -c "create user contributor with
      encrypted password 'PASS'" template1
xxx shouldn't we do the next line too? grant usage on schema ...
  $ psql -c "grant usage on schema SI, SI_Notify to contributor" seaice
  $ psql -c "grant select, insert, update, delete on all tables
      in schema SI, SI_Notify to contributor" seaice

Add the configuration to '.seaice': 

  [contributor]
  dbname = seaice
  user = contributor
  password = PASS

XXXX move this last few lines after [dev] and [heroku] are set up
xxx  and/or add --deploy=dev so that local instance can come up
     without having to configure heroku section
The web user interface creates a database connection pool with the 
same role. You can specify this on the command line: 

  $ ./ice.py --role=contributor --config=.seaice
  $ ./ice.py --role=contributor --config=local_deploy/.seaice

'--role' defaults to 'default'. 


## 5.5 OAuth credentials and app key

YAMZ uses Google for third party authentication (OAuth-2.0) management of 
logins. Visit https://console.developers.google.com to set this service up 
for your instance. Navigate to something like API Manager -> Credentials
and select whatever lets you create a new OAauth client ID.  For local
configuration, supply these answers:
 
 Application type . . . . . . . . . . Web application
 Authorized javascript origins  . . . http://localhost:5000 
 Authorized redirect URI  . . . . . . http://localhost:5000/authorized 

Create another set of credentials for your heroku instance, say yamz-dev:

 Application type . . . . . . . . . . Web application
 Authorized javascript origins  . . . http://yamz-dev.herokuapp.com
 Authorized redirect URI  . . . . . . http://yamz-dev.herokuapp.com/authorized 

In each case, you should obtain a pair of values to put into another
configuration file called '.seaice_auth'.  Create or edit this file,
replacing google_client_id with the returned 'Client ID' and replacing
google_client_secret with the returned 'Client secret'.

xxx Where does app_secret come in? does it come from the 'API key'?
    Manoj: app_secret only needed for heroku deployment

(See section 2.) XXX Are the instructions there complete, eg, redirect URL?) 
XXX ?document this in a 0.x section, since it applies to local and heroku?

Next, create a configuration file called '.seaice_auth' with the appropriate 
client IDs and secret keys. For instance, you may have credentials for 
'http://localhost:5000', as well as a deployment on heroku: 

XXX the google_client_id identifies your client software/(app?) and is
    paired with the redirect URL, eg, one for 'http://localhost:5000'
    and another for http://yamz.net...
xxx is this correct? each unique post-auth redirection target needs its
    own unique google_client_id
XXX to do: allow local dev to take place offline, ie, without contact
     with google for Auth or with minters and binders and n2t
xxx to do: let people create test terms that expire in two weeks

  [dev]
  google_client_id = 000-fella.apps.googleusercontent.com
  google_client_secret = SECRET1
  app_secret = SECRET2

  [heroku]
  google_client_id = 000-guy.apps.googleusercontent.com
  google_client_secret = SECRET3
  app_secret = SECRET4

IMPORTANT NOTE: A template of this file is provided in the github
repository. This file should remain secret and must not be published. 
We provide the template, since heroku requires a commited file. 

For convenience, this file will also keep the Flask app's secret key. For 
this key, enter a long, random string of characters. Finally, set the correct 
file permissions with: 

  $ chmod 600 .seaice_auth


## 5.6 N2T persistent identifier resolver credentials

Whenever a new term is created, YAMZ uses an API to n2t.net (maintained by
the California Digital Library) in order to generate ("mint") a persistent
identifier.  The main role of n2t.net is to be a resolver for the public-
facing URLs that persistently identify YAMZ terms.  It is necessary to
provide a minter password for API access to this web service.  To do so
include a line in ".seaice_auth" for every view:
 
   minter_password = PASS

A password found in the MINTER_PASSWORD environment variable, however, will
be preferred over the file setting.  This password is used again in the
API call to store metadata in a YAMZ binder on n2t.net.  The main bit of
metadata stored is the redirection target URL that supports resolution of
ARK identifiers for YAMZ terms.

Because real identifiers are meant to be persistent, no local or test
instance of YAMZ should ever set the boolean "prod_mode" parameter in
".seaice_auth".  For such instances the generated and updated terms
should just be for identifiers meant to be thrown away.  Only on the
real production instance of YAMZ, when you're done testing term creation
and update, should it be set to "enable" (the default is don't enable).


## 5.7 Test the instance

First, create the database schema: 

   $ ./sea --config=.seaice --init-db

Start the local server with: 
 
  $ ./ice.py --config=.seaice --deploy=dev

If all goes well, you should be able to navigate to your server by typing 
'http://localhost:5000' in the address bar. To verify that you've set up 
Google OAuth-2.0 correctly, try logging in. This will create an account.
Try adding a new term, modifying and deleting a term, and commenting on 
terms. To classify a term, do: 

  $ ./sea.py --config=.seaice --classify-terms