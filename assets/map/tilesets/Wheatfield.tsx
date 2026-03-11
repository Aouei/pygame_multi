<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.10" tiledversion="1.11.2" name="Wheatfield" tilewidth="16" tileheight="16" tilecount="4" columns="4">
 <image source="Wheatfield.png" width="64" height="16"/>
 <tile id="0" type="player_spawn">
  <objectgroup draworder="index" id="2">
   <object id="1" x="1" y="4" width="14" height="11"/>
  </objectgroup>
 </tile>
 <tile id="1" type="player_spawn">
  <objectgroup draworder="index" id="2">
   <object id="1" x="1" y="3" width="14" height="12"/>
  </objectgroup>
 </tile>
 <tile id="2" type="player_spawn">
  <properties>
   <property name="collision" type="bool" value="true"/>
  </properties>
  <objectgroup draworder="index" id="2">
   <object id="1" x="1" y="2" width="14" height="13"/>
   <object id="2" x="1" y="2" width="14" height="13"/>
   <object id="3" x="1" y="2" width="14" height="13"/>
  </objectgroup>
 </tile>
 <tile id="3" type="player_spawn">
  <objectgroup draworder="index" id="2">
   <object id="1" x="1" y="1" width="14" height="14"/>
  </objectgroup>
 </tile>
</tileset>
