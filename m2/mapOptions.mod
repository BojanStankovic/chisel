(* Copyright (C) 2015 Free Software Foundation, Inc.  *)
(* This file is part of Chisel.

Chisel is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free
Software Foundation; either version 3, or (at your option) any later
version.

Chisel is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License along
with gm2; see the file COPYING.  If not, write to the Free Software
Foundation, 51 Franklin Street, Fifth Floor,
Boston, MA 02110-1301, USA.  *)

IMPLEMENTATION MODULE mapOptions ;   (*!m2pim*)


VAR
   debug: BOOLEAN ;


(*
   debugging - is debugging mode set on?
*)

PROCEDURE debugging () : BOOLEAN ;
BEGIN
   RETURN debug
END debugging ;


(*
   setDebugging - set debugging to, on.
*)

PROCEDURE setDebugging (on: BOOLEAN) ;
BEGIN
   debug := on
END setDebugging ;


BEGIN
   setDebugging (FALSE)
END mapOptions.
