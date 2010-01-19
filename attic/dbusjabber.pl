#!/usr/bin/perl -w
# Copyright (c) 2008, Jonathan Hitchcock
# Released under terms of the MIT/X/Expat Licence. See COPYING for details.

use warnings;
use strict;

use Net::DBus;
use Net::DBus::Reactor;
use Net::DBus::Service;
use Net::DBus::Object;
use Net::XMPP;

use Carp qw(confess cluck);

#$SIG{__WARN__} = sub { cluck $_[0] };
#$SIG{__DIE__} = sub { confess $_[0] };

package TestObject;

use base qw(Net::DBus::Object);
use Net::DBus::Exporter qw(org.ibid.IbidService);

sub new {
    my $class = shift;
    my $service = shift;
    my $self = $class->SUPER::new($service, "/org/ibid/IbidObject");
    bless $self, $class;
    return $self;
}

#Message(from, resource, time, body)
dbus_signal("Message", ["string", "string", "string", "string"]);
sub emitMessage {
    my $self = shift;
    return $self->emit_signal("Message", $_[0], $_[1], time(), $_[2]);
}

package main;

my $server = 'jabber.org';
my $port = '5222';
my $username = 'ibidbot';
my $password = 'ibiddev';
my $resource = 'perl';

$SIG{HUP} = \&Stop; $SIG{KILL} = \&Stop; $SIG{TERM} = \&Stop; $SIG{INT} = \&Stop;

my $Connection = new Net::XMPP::Client();
#$Connection->SetCallBacks(message=>\&InMessage,
#                          presence=>\&InPresence,
#                          iq=>\&InIQ);

$Connection->SetPresenceCallBacks("available" => \&HandlePresence,
                                  "unavailable" => \&HandlePresence,
                                  "subscribe" => \&HandlePresence,
                                  "unsubscribe" => \&HandlePresence,
                                  "subscribed" => \&HandlePresence,
                                  "unsubscribed" => \&HandlePresence,
                                  "probe" => \&HandlePresence,
                                  "error" => \&HandlePresence);
$Connection->SetMessageCallBacks("normal" => \&HandleMessage,
                                 "chat" => \&HandleMessage,
                                 "groupchat" => \&HandleMessage,
                                 "headline" => \&HandleMessage,
                                 "error" => \&HandleMessage);
#$Connection->SetIQCallBacks("get" => \&HandleIQ,
#                            "set" => \&HandleIQ,
#                            "result" => \&HandleIQ);

my $status = $Connection->Connect(hostname=>$server, port=>$port);
die("ERROR:  Jabber server is down or connection was not allowed. ($!)") if (!(defined($status)));

my @result = $Connection->AuthSend(username=>$username,
                                   password=>$password,
                                   resource=>$resource);
die("ERROR: Authorization failed: $result[0] - $result[1]") if ($result[0] ne "ok");
print "Logged in to $server:$port...\n";
print "Getting Roster to tell server to send presence info...\n";
$Connection->RosterGet();

print "Sending presence to tell world that we are logged in...\n";
$Connection->PresenceSend();

my $bus = Net::DBus->session();
my $service = $bus->export_service("org.designfu.TestService");
my $object = TestObject->new($service);

my $reactor = Net::DBus::Reactor->main();

my $timer = $reactor->add_timeout(10,
    Net::DBus::Callback->new(method => sub {
            $reactor->shutdown() if(!defined($Connection->Process(0.01)));
        }
    ));

$reactor->run();
exit(0);

sub Stop
{
    print "Exiting...\n";
    $Connection->Disconnect();
    exit(0);
}

sub HandleMessage {
    my $sid = shift;
    my $message = shift;
    
    my $type = $message->GetType();
    my $fromJID = $message->GetFrom("jid");
    
    my $from = $fromJID->GetUserID();
    my $resource = $fromJID->GetResource();
    my $subject = $message->GetSubject();
    my $body = $message->GetBody();
    print "[$type] <$from/$resource> ".($subject?"[$subject] ":"")."$body\n";
    $object->emitMessage($from, $resource, $body);
}

sub HandlePresence {
    my $sid = shift;
    my $presence = shift;
    
    my $from = $presence->GetFrom();
    my $type = $presence->GetType();
    my $status = $presence->GetStatus();
    print "* $from -> $type [$status]";
}

# vi: set et sta sw=4 ts=4:
