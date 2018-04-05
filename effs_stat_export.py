import inspect
import os
import platform
import re
import sys
import traceback
from optparse import AmbiguousOptionError, BadOptionError, OptionParser

from logbook import CRITICAL, DEBUG, ERROR, FingersCrossedHandler, INFO, Logger, NestedSetup, NullHandler, StreamHandler, TimedRotatingFileHandler, WARNING, \
    __version__ as logbook_version

import config

from math import log

try:
    import wxversion
except ImportError:
    wxversion = None

try:
    import sqlalchemy
except ImportError:
    sqlalchemy = None

pyfalog = Logger(__name__)

class PassThroughOptionParser(OptionParser):

    def _process_args(self, largs, rargs, values):
        while rargs:
            try:
                OptionParser._process_args(self, largs, rargs, values)
            except (BadOptionError, AmbiguousOptionError) as e:
                pyfalog.error("Bad startup option passed.")
                largs.append(e.opt_str)

usage = "usage: %prog [--root]"
parser = PassThroughOptionParser(usage=usage)
parser.add_option("-r", "--root", action="store_true", dest="rootsavedata", help="if you want pyfa to store its data in root folder, use this option", default=False)
parser.add_option("-w", "--wx28", action="store_true", dest="force28", help="Force usage of wxPython 2.8", default=False)
parser.add_option("-d", "--debug", action="store_true", dest="debug", help="Set logger to debug level.", default=False)
parser.add_option("-t", "--title", action="store", dest="title", help="Set Window Title", default=None)
parser.add_option("-s", "--savepath", action="store", dest="savepath", help="Set the folder for savedata", default=None)
parser.add_option("-l", "--logginglevel", action="store", dest="logginglevel", help="Set desired logging level [Critical|Error|Warning|Info|Debug]", default="Error")

(options, args) = parser.parse_args()

if options.rootsavedata is True:
    config.saveInRoot = True

# set title if it wasn't supplied by argument
if options.title is None:
    options.title = "pyfa %s%s - Python Fitting Assistant" % (config.version, "" if config.tag.lower() != 'git' else " (git)")

config.debug = options.debug

# convert to unicode if it is set
if options.savepath is not None:
    options.savepath = unicode(options.savepath)
config.defPaths(options.savepath)

try:
    # noinspection PyPackageRequirements
    import wx
except:
    exit_message = "Cannot import wxPython. You can download wxPython (2.8+) from http://www.wxpython.org/"
    raise PreCheckException(exit_message)

try:
    import requests
    config.requestsVersion = requests.__version__
except ImportError:
    raise PreCheckException("Cannot import requests. You can download requests from https://pypi.python.org/pypi/requests.")

import eos.db

#if config.saVersion[0] > 0 or config.saVersion[1] >= 7:
    # <0.7 doesn't have support for events ;_; (mac-deprecated)
config.sa_events = True
import eos.events

    # noinspection PyUnresolvedReferences
import service.prefetch  # noqa: F401

        # Make sure the saveddata db exists
if not os.path.exists(config.savePath):
    os.mkdir(config.savePath)

eos.db.saveddata_meta.create_all()


armorLinkShip = eos.db.searchFits('armor links')[0]
infoLinkShip = eos.db.searchFits('information links')[0]
shieldLinkShip =  eos.db.searchFits('shield links')[0]
skirmishLinkShip = eos.db.searchFits('skirmish links')[0]
import json

def processExportedHtml(fileLocation):
    output = open('./shipJSON.js', 'w')
    output.write('let shipJSON = JSON.stringify([')
    outputBaseline = open('./shipBaseJSON.js', 'w')
    outputBaseline.write('let shipBaseJSON = JSON.stringify([')
    shipCata = eos.db.getItemsByCategory('Ship')
    #shipCata = eos.db.getItem(638)
    #shipCata = eos.db.getMetaGroup(638)
    #shipCata = eos.db.getAttributeInfo(638)
    #shipCata = eos.db.getItemsByCategory('Traits')
    #shipCata = eos.db.getGroup('invtraits')
    #shipCata = eos.db.getCategory('Traits')
    from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Table
    from sqlalchemy.orm import relation, mapper, synonym, deferred
    from eos.db import gamedata_session
    from eos.db import gamedata_meta
    from eos.db.gamedata.metaGroup import metatypes_table, items_table
    from eos.db.gamedata.group import groups_table

    from eos.gamedata import AlphaClone, Attribute, Category, Group, Item, MarketGroup, \
        MetaGroup, AttributeInfo, MetaData, Effect, ItemEffect, Traits
    from eos.db.gamedata.traits import traits_table
    #shipCata = traits_table #categories_table
    #print shipCata
    #print shipCata.columns
    #print shipCata.categoryName
    #print vars(shipCata)
    data = category = gamedata_session.query(Category).all()
    #print data
    #print iter(data)
    eff = gamedata_session.query(Category).get(53) #Bonus (id14) #Effects (id 53)
    data = eff;
    #print eff
    #print vars(eff)
    things = []#[Category, MetaGroup, AttributeInfo, MetaData, Item, Attribute, Effect, ItemEffect, Traits]#, Attribute]
    if False:
         for dataTab in things :
             print 'Data for: ' + str(dataTab)
             try:
                 filter = dataTab.typeID == 638
             except:
                 filter = dataTab.ID == 638
                 data = gamedata_session.query(dataTab).options().filter(filter).all()
                 print data
                 try:
                     varDict = vars(data)
                     print varDict
                 except:
                     print 'Not a Dict'
                     try:
                         varDict = data.__doc__
                         print varDict
                     except:
                         print 'No items()'
                         try:
                             for varDict in data:
                                 print varDict
                                 print vars(varDict)
                         except:
                             print 'Not a list of dicts'

    #print vars(shipCata._sa_instance_state)
    baseLimit = 0
    baseN = 0
    nameReqBase = '';
    for ship in iter(shipCata):
        if baseN < baseLimit and nameReqBase in ship.name:
            dna = str(ship.ID)
            stats = setFitFromString(dna, ship.name, ship.groupID)
            outputBaseline.write(stats)
            outputBaseline.write(',\n')
            baseN += 1;
    limit = 0
    skipTill = 0
    nameReq = ''
    n = 0
    try:
        with open('pyfaFits.html'):
            fileLocation = 'pyfaFits.html'
    except:
        try:
            with open('.pyfa/pyfaFits.html'):
                fileLocation = '.pyfa/pyfaFits.html'
        except:
            try:
                with open('../.pyfa/pyfaFits.html'):
                    fileLocation = '../.pyfa/pyfaFits.html'
            except:
                try:
                    with open('../../.pyfa/pyfaFits.html'):
                        fileLocation = '../../.pyfa/pyfaFits.html'
                except:
                    fileLocation = None;
    fitList = eos.db.getFitList()
    with open(fileLocation) as f:
            for fit in fitList:
                if limit == None or n < limit:
                    n += 1
                    name = fit.ship.name + ': ' + fit.name
                    if n >= skipTill and nameReq in name:
                        stats = parseNeededFitDetails(fit, 0)
                        output.write(stats)
                        output.write(',\n')
    if False and fileLocation != None:
        with open(fileLocation) as f:
            for fullLine in f:
                if limit == None or n < limit:
                    n += 1
                    startInd = fullLine.find('/dna/') + 5
                    line = fullLine[startInd:len(fullLine)]
                    endInd = line.find('::')
                    dna = line[0:endInd]
                    name = line[line.find('>') + 1:line.find('<')]
                    if n >= skipTill and nameReq in name:
                        print 'name: ' + name + ' DNA: ' + dna
                        stats = setFitFromString(dna, name, 0)
                        output.write(stats)
                        output.write(',\n')
    output.write(']);\nexport {shipJSON};')
    output.close()
    outputBaseline.write(']);\nexport {shipBaseJSON};')
    outputBaseline.close()
def attrDirectMap(values, target, source):
    for val in values:
        target[val] = source.itemModifiedAttributes[val]
def parseNeededFitDetails(fit, groupID):
    singleRunPrintPreformed = False
    weaponSystems = []
    groups = {}
    moduleNames = []
    fitID = fit.ID
    if len(fit.modules) > 0:
        fit.name = fit.ship.name + ': ' + fit.name
    print ''
    print 'name: ' + fit.name
    fitL = Fit()
    fitL.recalc(fit)
    fit = eos.db.getFit(fitID)
    if False:
        from eos.db import gamedata_session
        from eos.gamedata import Group, Category
        filterVal = Group.categoryID == 6
        data = gamedata_session.query(Group).options().filter(filterVal).all()
        for group in data:
            print group.groupName + '  groupID: ' + str(group.groupID)
            #print group.categoryName + '  categoryID: ' + str(group.categoryID) + ', published: ' + str(group.published)
            #print vars(group)
            #print ''
        return ''
    projectedModGroupIds = [
        41, 52, 65, 67, 68, 71, 80, 201, 208, 291, 325, 379, 585,
        842, 899, 1150, 1154, 1189, 1306, 1672, 1697, 1698, 1815, 1894
    ]
    projectedMods = filter(lambda mod: mod.item and mod.item.groupID in projectedModGroupIds, fit.modules)

    unpropedSpeed = fit.maxSpeed
    unpropedSig = fit.ship.itemModifiedAttributes['signatureRadius']
    usingMWD = False
    propMods = filter(lambda mod: mod.item and mod.item.groupID in [46], fit.modules)
    possibleMWD = filter(lambda mod: 'signatureRadiusBonus' in mod.item.attributes, propMods)
    if len(possibleMWD) > 0 and possibleMWD[0].state > 0:
        mwd = possibleMWD[0]
        oldMwdState = mwd.state
        mwd.state = 0
        fitL.recalc(fit)
        fit = eos.db.getFit(fitID)
        unpropedSpeed = fit.maxSpeed
        unpropedSig = fit.ship.itemModifiedAttributes['signatureRadius']
        mwd.state = oldMwdState
        fitL.recalc(fit)
        fit = eos.db.getFit(fitID)
        usingMWD = True

    print fit.ship.itemModifiedAttributes['rigSize']
    print propMods
    mwdPropSpeed = fit.maxSpeed
    if groupID > 0:
        propID = None
        rigSize = fit.ship.itemModifiedAttributes['rigSize']
        if rigSize == 1 and fit.ship.itemModifiedAttributes['medSlots'] > 0:
            propID = 440
        elif rigSize == 2 and fit.ship.itemModifiedAttributes['medSlots'] > 0:
            propID = 12076
        elif rigSize == 3 and fit.ship.itemModifiedAttributes['medSlots'] > 0:
            propID = 12084
        elif rigSize == 4 and fit.ship.itemModifiedAttributes['medSlots'] > 0:
            if fit.ship.itemModifiedAttributes['powerOutput'] > 60000:
                propID = 41253
            else:
                propID = 12084
        elif rigSize == None and fit.ship.itemModifiedAttributes['medSlots'] > 0:
            propID = 440
        if propID:
            fitL.appendModule(fitID, propID)
            fitL.recalc(fit)
            fit = eos.db.getFit(fitID)
            mwdPropSpeed = fit.maxSpeed
            mwdPosition = filter(lambda mod: mod.item and mod.item.ID == propID, fit.modules)[0].position
            fitL.removeModule(fitID, mwdPosition)
            fitL.recalc(fit)
            fit = eos.db.getFit(fitID)

    projections = []
    for mod in projectedMods:
        stats = {}
        if mod.item.groupID == 65 or mod.item.groupID == 1672:
            stats['type'] = 'Stasis Web'
            stats['optimal'] = mod.itemModifiedAttributes['maxRange']
            attrDirectMap(['duration', 'speedFactor'], stats, mod)
        elif mod.item.groupID == 291:
            stats['type'] = 'Weapon Disruptor'
            stats['optimal'] = mod.itemModifiedAttributes['maxRange']
            stats['falloff'] = mod.itemModifiedAttributes['falloffEffectiveness']
            attrDirectMap([
                'trackingSpeedBonus', 'maxRangeBonus', 'falloffBonus', 'aoeCloudSizeBonus',\
                'aoeVelocityBonus', 'missileVelocityBonus', 'explosionDelayBonus'\
            ], stats, mod)
        elif mod.item.groupID == 68:
            stats['type'] = 'Energy Nosferatu'
            attrDirectMap(['powerTransferAmount', 'energyNeutralizerSignatureResolution'], stats, mod)
        elif mod.item.groupID == 71:
            stats['type'] = 'Energy Neutralizer'
            attrDirectMap([
                'energyNeutralizerSignatureResolution','entityCapacitorLevelModifierSmall',\
                'entityCapacitorLevelModifierMedium', 'entityCapacitorLevelModifierLarge',\
                'energyNeutralizerAmount'\
            ], stats, mod)
        elif mod.item.groupID == 41 or mod.item.groupID == 1697:
            stats['type'] = 'Remote Shield Booster'
            attrDirectMap(['shieldBonus'], stats, mod)
        elif mod.item.groupID == 325 or mod.item.groupID == 1698:
            stats['type'] = 'Remote Armor Repairer'
            attrDirectMap(['armorDamageAmount'], stats, mod)
        elif mod.item.groupID == 52:
            stats['type'] = 'Warp Scrambler'
            attrDirectMap(['activationBlockedStrenght', 'warpScrambleStrength'], stats, mod)
        elif mod.item.groupID == 379:
            stats['type'] = 'Target Painter'
            attrDirectMap(['signatureRadiusBonus'], stats, mod)
        elif mod.item.groupID == 208:
            stats['type'] = 'Sensor Dampener'
            attrDirectMap(['maxTargetRangeBonus', 'scanResolutionBonus'], stats, mod)
        elif mod.item.groupID == 201:
            stats['type'] = 'ECM'
            attrDirectMap([
                'scanGravimetricStrengthBonus', 'scanMagnetometricStrengthBonus',\
                'scanRadarStrengthBonus', 'scanLadarStrengthBonus',\
            ], stats, mod)
        elif mod.item.groupID == 80:
            stats['type'] = 'Burst Jammer'
            mod.itemModifiedAttributes['maxRange'] = mod.itemModifiedAttributes['ecmBurstRange']
            attrDirectMap([
                'scanGravimetricStrengthBonus', 'scanMagnetometricStrengthBonus',\
                'scanRadarStrengthBonus', 'scanLadarStrengthBonus',\
            ], stats, mod)
        elif mod.item.groupID == 1189:
            stats['type'] = 'Micro Jump Drive'
            mod.itemModifiedAttributes['maxRange'] = 0
            attrDirectMap(['moduleReactivationDelay'], stats, mod)
        if mod.itemModifiedAttributes['maxRange'] == None:
            print mod.item.name
            print mod.itemModifiedAttributes.items()
            raise ValueError('Projected module lacks a maxRange')
        stats['optimal'] = mod.itemModifiedAttributes['maxRange']
        stats['falloff'] = mod.itemModifiedAttributes['falloffEffectiveness'] or 0
        attrDirectMap(['duration', 'capacitorNeed'], stats, mod)
        projections.append(stats)
        #print ''
        #print stats
        #print mod.item.name
        #print mod.itemModifiedAttributes.items()
        #print ''
        #print vars(mod.item)
    #print vars(web.itemModifiedAttributes)
    #print vars(fit.modules)
    #print vars(fit.modules[0])
    highSlotNames = []
    midSlotNames = []
    lowSlotNames = []
    rigSlotNames = []
    miscSlotNames = [] #subsystems ect
    for mod in fit.modules:
        if mod.slot == 3:
            modSlotNames = highSlotNames
        elif mod.slot == 2:
            modSlotNames = midSlotNames
        elif mod.slot == 1:
            modSlotNames = lowSlotNames
        elif mod.slot == 4:
            modSlotNames = rigSlotNames
        elif mod.slot == 5:
            modSlotNames = miscSlotNames
        try:
            if mod.item != None:
                if mod.charge != None:
                    modSlotNames.append(mod.item.name + ':  ' + mod.charge.name)
                else:
                    modSlotNames.append(mod.item.name)
            else:
                modSlotNames.append('Empty Slot')
        except:
            print vars(mod)
            print 'could not find name for module'
            print fit.modules
        if mod.dps > 0:
            keystr = str(mod.itemID) + '-' + str(mod.chargeID)
            if keystr in groups:
                groups[keystr][1] += 1
            else:
                groups[keystr] = [mod, 1]
    for modInfo in [['High Slots:'], highSlotNames, ['', 'Med Slots:'], midSlotNames, ['', 'Low Slots:'], lowSlotNames, ['', 'Rig Slots:'], rigSlotNames]:
        moduleNames.extend(modInfo)
    if len(miscSlotNames) > 0:
        moduleNames.append('')
        moduleNames.append('Subsystems:')
        moduleNames.extend(miscSlotNames)
    droneNames = []
    fighterNames = []
    for drone in fit.drones:
        if drone.amountActive > 0:
            droneNames.append(drone.item.name)
    for fighter in fit.fighters:
        if fighter.amountActive > 0:
            fighterNames.append(fighter.item.name)
    if len(droneNames) > 0:
        moduleNames.append('')
        moduleNames.append('Drones:')
        moduleNames.extend(droneNames)
    if len(fighterNames) > 0:
        moduleNames.append('')
        moduleNames.append('Fighters:')
        moduleNames.extend(fighterNames)
    if len(fit.implants) > 0:
        moduleNames.append('')
        moduleNames.append('Implants:')
        for implant in fit.implants:
            moduleNames.append(implant.item.name)
    if len(fit.commandFits) > 0:
        moduleNames.append('')
        moduleNames.append('Command Fits:')
        for commandFit in fit.commandFits:
            moduleNames.append(commandFit.name)

    for wepGroup in groups:
        stats = groups[wepGroup][0]
        c = groups[wepGroup][1]
        tracking = 0
        maxVelocity = 0
        explosionDelay = 0
        damageReductionFactor = 0
        explosionRadius = 0
        explosionVelocity = 0
        aoeFieldRange = 0
        if stats.hardpoint == 2:
            tracking = stats.itemModifiedAttributes['trackingSpeed']
            typeing = 'Turret'
            name = stats.item.name + ', ' + stats.charge.name
        elif stats.hardpoint == 1 or 'Bomb Launcher' in stats.item.name:
            maxVelocity = stats.chargeModifiedAttributes['maxVelocity']
            explosionDelay = stats.chargeModifiedAttributes['explosionDelay']
            damageReductionFactor = stats.chargeModifiedAttributes['aoeDamageReductionFactor']
            explosionRadius = stats.chargeModifiedAttributes['aoeCloudSize']
            explosionVelocity = stats.chargeModifiedAttributes['aoeVelocity']
            typeing = 'Missile'
            name = stats.item.name + ', ' + stats.charge.name
        elif stats.hardpoint == 0:
            aoeFieldRange = stats.itemModifiedAttributes['empFieldRange']
            typeing = 'SmartBomb'
            name = stats.item.name
        statDict = {'dps': stats.dps * c, 'capUse': stats.capUse * c, 'falloff': stats.falloff,\
                    'type': typeing, 'name': name, 'optimal': stats.maxRange,\
                    'numCharges': stats.numCharges, 'numShots': stats.numShots, 'reloadTime': stats.reloadTime,\
                    'cycleTime': stats.cycleTime, 'volley': stats.volley * c, 'tracking': tracking,\
                    'maxVelocity': maxVelocity, 'explosionDelay': explosionDelay, 'damageReductionFactor': damageReductionFactor,\
                    'explosionRadius': explosionRadius, 'explosionVelocity': explosionVelocity, 'aoeFieldRange': aoeFieldRange\
        }
        weaponSystems.append(statDict)
        #if fit.droneDPS > 0:
    for drone in fit.drones:
        if drone.dps[0] > 0 and drone.amountActive > 0:
            newTracking =  drone.itemModifiedAttributes['trackingSpeed'] / (drone.itemModifiedAttributes['optimalSigRadius'] / 40000)
            statDict = {'dps': drone.dps[0], 'cycleTime': drone.cycleTime, 'type': 'Drone',\
                        'optimal': drone.maxRange, 'name': drone.item.name, 'falloff': drone.falloff,\
                        'maxSpeed': drone.itemModifiedAttributes['maxVelocity'], 'tracking': newTracking,\
                        'volley': drone.dps[1]\
            }
            weaponSystems.append(statDict)
    for fighter in fit.fighters:
        if fighter.dps[0] > 0 and fighter.amountActive > 0:
            abilities = []
            #for ability in fighter.abilities:
            if 'fighterAbilityAttackMissileDamageEM' in fighter.itemModifiedAttributes:
                baseRef = 'fighterAbilityAttackMissile'
                baseRefDam = baseRef + 'Damage'
                damageReductionFactor = log(fighter.itemModifiedAttributes[baseRef + 'ReductionFactor']) / log(fighter.itemModifiedAttributes[baseRef + 'ReductionSensitivity'])
                abBaseDamage = fighter.itemModifiedAttributes[baseRefDam + 'EM'] + fighter.itemModifiedAttributes[baseRefDam + 'Therm'] + fighter.itemModifiedAttributes[baseRefDam + 'Exp'] + fighter.itemModifiedAttributes[baseRefDam + 'Kin']
                abDamage = abBaseDamage * fighter.itemModifiedAttributes[baseRefDam + 'Multiplier']
                ability = {'name': 'RegularAttack', 'volley': abDamage * fighter.amountActive, 'explosionRadius': fighter.itemModifiedAttributes[baseRef + 'ExplosionRadius'],\
                           'explosionVelocity': fighter.itemModifiedAttributes[baseRef + 'ExplosionVelocity'], 'optimal': fighter.itemModifiedAttributes[baseRef + 'RangeOptimal'],\
                           'damageReductionFactor': damageReductionFactor, 'rof': fighter.itemModifiedAttributes[baseRef + 'Duration'],\
                }
                abilities.append(ability)
            if 'fighterAbilityMissilesDamageEM' in fighter.itemModifiedAttributes:
                baseRef = 'fighterAbilityMissiles'
                baseRefDam = baseRef + 'Damage'
                damageReductionFactor = log(fighter.itemModifiedAttributes[baseRefDam + 'ReductionFactor']) / log(fighter.itemModifiedAttributes[baseRefDam + 'ReductionSensitivity'])
                abBaseDamage = fighter.itemModifiedAttributes[baseRefDam + 'EM'] + fighter.itemModifiedAttributes[baseRefDam + 'Therm'] + fighter.itemModifiedAttributes[baseRefDam + 'Exp'] + fighter.itemModifiedAttributes[baseRefDam + 'Kin']
                abDamage = abBaseDamage * fighter.itemModifiedAttributes[baseRefDam + 'Multiplier']
                ability = {'name': 'MissileAttack', 'volley': abDamage * fighter.amountActive, 'explosionRadius': fighter.itemModifiedAttributes[baseRef + 'ExplosionRadius'],\
                           'explosionVelocity': fighter.itemModifiedAttributes[baseRef + 'ExplosionVelocity'], 'optimal': fighter.itemModifiedAttributes[baseRef + 'Range'],\
                           'damageReductionFactor': damageReductionFactor, 'rof': fighter.itemModifiedAttributes[baseRef + 'Duration'],\
                }
                abilities.append(ability)
            statDict = {'dps': fighter.dps[0], 'type': 'Fighter', 'name': fighter.item.name,\
                        'maxSpeed': fighter.itemModifiedAttributes['maxVelocity'], 'abilities': abilities, 'ehp': fighter.itemModifiedAttributes['shieldCapacity'] / 0.8875 * fighter.amountActive,\
                        'volley': fighter.dps[1], 'signatureRadius': fighter.itemModifiedAttributes['signatureRadius']\
            }
            weaponSystems.append(statDict)
    turretSlots = fit.ship.itemModifiedAttributes['turretSlotsLeft']
    launcherSlots = fit.ship.itemModifiedAttributes['launcherSlotsLeft']
    droneBandwidth = fit.ship.itemModifiedAttributes['droneBandwidth']
    if turretSlots == None:
        turretSlots = 0
    if launcherSlots == None:
        launcherSlots = 0
    if droneBandwidth == None:
        droneBandwidth = 0
    effectiveTurretSlots = turretSlots
    effectiveLauncherSlots = launcherSlots
    effectiveDroneBandwidth = droneBandwidth
    from eos.db import gamedata_session
    from eos.gamedata import Traits
    filterVal = Traits.typeID == fit.shipID
    data = gamedata_session.query(Traits).options().filter(filterVal).all()
    roleBonusMode = False
    if len(data) != 0:
        #print data[0].traitText
        previousTypedBonus = 0
        previousDroneTypeBonus = 0
        for bonusText in data[0].traitText.splitlines():
            bonusText = bonusText.lower()
            #print 'bonus text line: ' + bonusText
            if 'per skill level' in bonusText:
                roleBonusMode = False
            if 'role bonus' in bonusText or 'misc bonus' in bonusText:
                roleBonusMode = True
            multi = 1
            if 'damage' in bonusText and not any(e in bonusText for e in ['control', 'heat']):#'control' in bonusText and not 'heat' in bonusText:
                splitText = bonusText.split('%')
                if (float(splitText[0]) > 0) == False:
                    print 'damage bonus split did not parse correctly!'
                    print float(splitText[0])
                if roleBonusMode:
                    addedMulti = float(splitText[0])
                else:
                    addedMulti = float(splitText[0]) * 5
                if any(e in bonusText for e in [' em', 'thermal', 'kinetic', 'explosive']):
                    if addedMulti > previousTypedBonus:
                            previousTypedBonus = addedMulti
                    else:
                        addedMulti = 0
                if any(e in bonusText for e in ['heavy drone', 'medium drone', 'light drone', 'sentry drone']):
                    if addedMulti > previousDroneTypeBonus:
                            previousDroneTypeBonus = addedMulti
                    else:
                        addedMulti = 0
                multi = 1 + (addedMulti / 100)
            elif 'rate of fire' in bonusText:
                splitText = bonusText.split('%')
                if (float(splitText[0]) > 0) == False:
                    print 'rate of fire bonus split did not parse correctly!'
                    print float(splitText[0])
                if roleBonusMode:
                    rofMulti = float(splitText[0])
                else:
                    rofMulti = float(splitText[0]) * 5
                multi = 1 / (1 - (rofMulti / 100))
            if multi > 1:
                if 'drone' in bonusText.lower():
                    effectiveDroneBandwidth *= multi
                elif 'turret' in bonusText.lower():
                    effectiveTurretSlots *= multi
                elif any(e in bonusText for e in ['missile', 'torpedo']):
                    effectiveLauncherSlots *= multi
    if groupID == 485:
        effectiveTurretSlots *= 9.4
        effectiveLauncherSlots *= 15
    effectiveTurretSlots = round(effectiveTurretSlots, 2);
    effectiveLauncherSlots = round(effectiveLauncherSlots, 2);
    effectiveDroneBandwidth = round(effectiveDroneBandwidth, 2);
    hullResonance = {'exp': fit.ship.itemModifiedAttributes['explosiveDamageResonance'], 'kin': fit.ship.itemModifiedAttributes['kineticDamageResonance'], \
                     'therm': fit.ship.itemModifiedAttributes['thermalDamageResonance'], 'em': fit.ship.itemModifiedAttributes['emDamageResonance']}
    armorResonance = {'exp': fit.ship.itemModifiedAttributes['armorExplosiveDamageResonance'], 'kin': fit.ship.itemModifiedAttributes['armorKineticDamageResonance'], \
                      'therm': fit.ship.itemModifiedAttributes['armorThermalDamageResonance'], 'em': fit.ship.itemModifiedAttributes['armorEmDamageResonance']}
    shieldResonance = {'exp': fit.ship.itemModifiedAttributes['shieldExplosiveDamageResonance'], 'kin': fit.ship.itemModifiedAttributes['shieldKineticDamageResonance'], \
                       'therm': fit.ship.itemModifiedAttributes['shieldThermalDamageResonance'], 'em': fit.ship.itemModifiedAttributes['shieldEmDamageResonance']}
    resonance = {'hull': hullResonance, 'armor': armorResonance, 'shield': shieldResonance}
    shipSizes = ['Frigate', 'Destroyer', 'Cruiser', 'Battlecruiser', 'Battleship', 'Capital', 'Industrial', 'Misc']
    if groupID in [25, 31, 237, 324, 830, 831, 834, 893, 1283, 1527]:
        shipSize = shipSizes[0]
    elif groupID in [420, 541, 1305, 1534]:
        shipSize = shipSizes[1]
    elif groupID in [26, 358, 832, 833, 894, 906, 963]:
        shipSize = shipSizes[2]
    elif groupID in [419, 540, 1201]:
        shipSize = shipSizes[3]
    elif groupID in [27, 381, 898, 900]:
        shipSize = shipSizes[4]
    elif groupID in [30, 485, 513, 547, 659, 883, 902, 1538]:
        shipSize = shipSizes[5]
    elif groupID in [28, 380, 1202, 463, 543, 941]:
        shipSize = shipSizes[6]
    elif groupID in [29, 1022]:
        shipSize = shipSizes[7]
    else:
        shipSize = 'ShipSize not found for ' + fit.name + ' groupID: ' + str(groupID)
        print shipSize
    try:
        parsable =  {'name': fit.name, 'ehp': fit.ehp, 'droneDPS': fit.droneDPS, \
                     'droneVolley': fit.droneVolley, 'hp': fit.hp, 'maxTargets': fit.maxTargets, \
                     'maxSpeed': fit.maxSpeed, 'weaponVolley': fit.weaponVolley, 'totalVolley': fit.totalVolley,\
                     'maxTargetRange': fit.maxTargetRange, 'scanStrength': fit.scanStrength,\
                     'weaponDPS': fit.weaponDPS, 'alignTime': fit.alignTime, 'signatureRadius': fit.ship.itemModifiedAttributes['signatureRadius'],\
                     'weapons': weaponSystems, 'scanRes': fit.ship.itemModifiedAttributes['scanResolution'],\
                     'projectedModules': fit.projectedModules, 'capUsed': fit.capUsed, 'capRecharge': fit.capRecharge,\
                     'rigSlots': fit.ship.itemModifiedAttributes['rigSlots'], 'lowSlots': fit.ship.itemModifiedAttributes['lowSlots'],\
                     'midSlots': fit.ship.itemModifiedAttributes['medSlots'], 'highSlots': fit.ship.itemModifiedAttributes['hiSlots'],\
                     'turretSlots': fit.ship.itemModifiedAttributes['turretSlotsLeft'], 'launcherSlots': fit.ship.itemModifiedAttributes['launcherSlotsLeft'],\
                     'powerOutput': fit.ship.itemModifiedAttributes['powerOutput'], 'rigSize': fit.ship.itemModifiedAttributes['rigSize'],\
                     'effectiveTurrets': effectiveTurretSlots, 'effectiveLaunchers': effectiveLauncherSlots, 'effectiveDroneBandwidth': effectiveDroneBandwidth,\
                     'resonance': resonance, 'typeID': fit.shipID, 'groupID': groupID, 'shipSize': shipSize,\
                     'droneControlRange': fit.ship.itemModifiedAttributes['droneControlRange'], 'mass': fit.ship.itemModifiedAttributes['mass'],\
                     'moduleNames': moduleNames, 'projections': projections, 'unpropedSpeed': unpropedSpeed, 'unpropedSig': unpropedSig,\
                     'usingMWD': usingMWD, 'mwdPropSpeed': mwdPropSpeed
        }
    except TypeError:
        print 'Error parsing fit:' + str(fit)
        print TypeError
        parsable = {'name': fit.name + 'Fit could not be correctly parsed'}
        #print fit.ship.itemModifiedAttributes.items()
        #help(fit)
        #if len(fit.fighters) > 5:
        #print fit.fighters
        #help(fit.fighters[0])
    stringified = json.dumps(parsable, skipkeys=True)
    return stringified
def setFitFromString(dnaString, fitName, groupID) :
    modArray = dnaString.split(':')
    additionalModeFit = ''
    #if groupID == 485 and len(modArray) == 1:
        #additionalModeFit = ',\n' + setFitFromString(dnaString + ':4292', fitName + ' (Sieged)', groupID)
    fitL = Fit()
    print modArray[0]
    fitID = fitL.newFit(int(modArray[0]), fitName)
    fit = eos.db.getFit(fitID)
    ammoArray = []
    n = -1
    for mod in iter(modArray):
        n = n + 1
        if n > 0:
            #print n
            #print mod
            modSp = mod.split(';')
            if len(modSp) == 2:
                k = 0
                while k < int(modSp[1]):
                    k = k + 1
                    itemID = int(modSp[0])
                    item = eos.db.getItem(int(modSp[0]), eager=("attributes", "group.category"))
                    cat = item.category.name
                    if cat == 'Drone':
                        fitL.addDrone(fitID, itemID, int(modSp[1]), recalc=False)
                        k += int(modSp[1])
                    if cat == 'Fighter':
                        fitL.addFighter(fitID, itemID, recalc=False)
                        #fit.fighters.last.abilities.active = True
                        k += 100
                    if fitL.isAmmo(int(modSp[0])):
                        k += 100
                        ammoArray.append(int(modSp[0]));
                    fitL.appendModule(fitID, int(modSp[0]))
    fit = eos.db.getFit(fitID)
    #nonEmptyModules = fit.modules
    #while nonEmptyModules.find(None) >= 0:
    #   print 'ssssssssssssssss'
    #   nonEmptyModules.remove(None)
    for ammo in iter(ammoArray):
        fitL.setAmmo(fitID, ammo, filter(lambda mod: str(mod).find('name') > 0, fit.modules))
    if len(fit.drones) > 0:
        fit.drones[0].amountActive = fit.drones[0].amount
        eos.db.commit()
    for fighter in iter(fit.fighters):
        for ability in fighter.abilities:
            if ability.effect.handlerName == u'fighterabilityattackm' and ability.active == True:
                for abilityAltRef in fighter.abilities:
                    if abilityAltRef.effect.isImplemented:
                        abilityAltRef.active = True
    fitL.recalc(fit)
    fit = eos.db.getFit(fitID)
    print filter(lambda mod: mod.item.groupID in [1189, 658], fit.modules)
    #fit.calculateWeaponStats()
    fitL.addCommandFit(fit.ID, armorLinkShip)
    fitL.addCommandFit(fit.ID, shieldLinkShip)
    fitL.addCommandFit(fit.ID, skirmishLinkShip)
    fitL.addCommandFit(fit.ID, infoLinkShip)
    #def anonfunc(unusedArg): True
    jsonStr = parseNeededFitDetails(fit, groupID)
    #print vars(fit.ship._Ship__item)
    #help(fit)
    Fit.deleteFit(fitID)
    return jsonStr + additionalModeFit
launchUI = False
#launchUI = True
if launchUI == False:
    from service.fit import Fit
    #setFitFromString(dnaChim, 'moMachsD')
    #help(eos.db.getItem)
    #ship = es_Ship(eos.db.getItem(27))
    processExportedHtml('../.pyfa/pyfaFits.html')
