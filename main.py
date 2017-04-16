import argparse
import sys
import logging
from pprint import pprint
from modules.bcolors.bcolors import bcolors

from modules.core.Game import Game
from modules.core.PlayerAssessment import PlayerAssessmentBSONHandler, PlayerAssessment
from modules.core.PlayerAssessments import PlayerAssessments
from modules.core.GameAnalysis import GameAnalysis
from modules.core.PlayerAnalysis import PlayerAnalysis

from modules.core.recentGames import recentGames

from modules.irwin.updatePlayerEngineStatus import isEngine

from Env import Env

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("token", metavar="TOKEN",
                    help="secret token for the lichess api")
parser.add_argument("learn", metavar="LEARN",
                    help="does this bot learn", nargs="?", type=int, default=1)
parser.add_argument("threads", metavar="THREADS", nargs="?", type=int, default=4,
                    help="number of engine threads")
parser.add_argument("memory", metavar="MEMORY", nargs="?", type=int, default=2048,
                    help="memory in MB to use for engine hashtables")
parser.add_argument("--quiet", dest="loglevel",
                    default=logging.DEBUG, action="store_const", const=logging.INFO,
                    help="substantially reduce the number of logged messages")
settings = parser.parse_args()

try:
  # Optionally fix colors on Windows and in journals if the colorama module
  # is available.
  import colorama
  wrapper = colorama.AnsiToWin32(sys.stdout)
  if wrapper.should_wrap():
    sys.stdout = wrapper.stream
except ImportError:
  pass

logging.basicConfig(format="%(message)s", level=settings.loglevel, stream=sys.stdout)
logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
logging.getLogger("chess.uci").setLevel(logging.WARNING)

env = Env(settings)

engines = ['frankenste1n', 'farhan_fc', 'ronperu', 'zubakinp', 'zubakinpavel', 'marinaprit27', 'namaku_sapa1', 'xlesss', 'eriel', 'szlevi2000', 'nabeghe81', 'master_rhodok', 'egorsidorin', 'tommy-supriyanto',
  'macaroniandchess', 'pavel_shovunov', 'mrzerial', 'mitchflo', 'olsaintnick', 'not_that_bad', 'the-gres', 'bobbyisback', 'shadowblade1', 'markus_s', 'hazael88', 'ruslanchik53', 'njalsaga1970', 'thdames', 'kb1900',
  'djdjus', 'bullet33444', 'samuerl', 'markdiaz', 'drohn64', 'stormcat', 'arialish', 'nillonator', 'ennaque', 'bennyyush', 'dark_knight_666', 'stevankacicka789', 'ja007', 'youssoupov25121970', 'kofeto94', 'cajetudo',
  'satrancsever1', 'namoni', 'osamukitajima', 'sumo1111', 'hossamkamalhk1', 'flashsplash', 'andr009', 'drnajafzade1987', 'tosssmana', 'pishi_gg_wp', 'mrtopiary', 'jakkel', 'darkblue98', 'grandpatzer3000', 'anvar3955',
  'capturedpawn', 'mohammad_zain', 'agrig19chess', 'delilled', 'sparadrap', 'doubleplayer', 'p43', 'iprogrammer', 'poci01', 'chesscoachua', 'chemicalking', 'dislikeofpeople', 'lil-zeeshan', 'gwt', 'ballado_2239',
  'psyhtrance', 'eleazaralsisto11', 'bobby_ocean', 'gogpro', 'coolabbey2010', 'jchosenchess', 'billonachess', 'urvish', 'gnp', 'maksim_morozov', 'emadmiqdad', 'blakesekelsky', 'banjalukaman', 'arcanjo321',
  'miguelito1965', 'fernandofurman', 'tevipigui', 'rindane', 'dutchbill', 'dkjsfldkjfsldjfl', 'elinombrable', 'boltok', 'lvpartisan', 'killservice', 'ivanoff_ru', 'markus_solar', 'hooster', 'flexo54', 'juandy1945',
  'shaiapouf', 'craigmandimutsira', 'hansenwang6900', 'evematesurra1', 'corridoio97', 'jonaspio', 'elholios', 'chessanomaly94', 'davidelliottclaveau', 'pekkejosue', 'ariobarzan12', 'delta1king', 'pashapash', 'jkgu', 
  'nollan', 'obvandy', 'ezlevi', 'iramevol', 'dontunderestimateme', 'nemo_centaur', 'artofscript', 'warped_perception', 'stupidcanvas', 'lllll-lllll', 'coolabe20', 'kiran01', 'forte130', 'khald777', 'fastbull', 'da1er',
  'wilco_11111', 'xhuli002', 'cemalkaragunlu', 'chesselminster', 'therunningpawn', 'gmeli', 'hypnosfujy', 'thegoldenlight', 'srv236', 'yudiajafans', 'azadiazadiam', 'ilovepolinar', 'thepinkpanter', 'suleyman2005',
  'sankalpistheking', 'kiyaku', 'nitewalker', 'chessdevtwitch', 'mchammer007', 'lebordeian', 'tadhg36', 'jorgii5', 'dexadox', 'loguantzung', 'aromagrandcoffe', 'f_w_nietzsche', 'fri_w_nietzsche', 'starworldx11',
  'caganaras', 'abotrika', 'farzad-hasani', 'mh1395', 'maxmajibiu', 'matsella', 'wpbet', 'argentinapanyvino', 'thechessnoobs-yt', 'lotek', 'jegerikkejeg', 'lmtuzov', 'reza-abdolmaleki12', 'michael_mikic', 'adammurphy24',
  'drogor', 'rassto', 'mo2', 'xtalxx', 'kramerinho', 'stronghold_legend', 'ahmed-97', 'abiicias', 'benf97', 'zelao', 'reza2016', 'muflin01', 'sertinho0', 'certeiro', 'pedrogawa', 'mstak_noob', 'musuhkucemen1',
  'musuhkucemen02', 'grinlog', 'sunbank', 'chess244', 'derpapast', 'wont_let_me_register', 'gt5254', 'elifalet', 'guy0308', 'corotagialla', 'lotthek', 'obssceniity', 'jxvier', 'beliy-slon', 'en1gm4', 'funnn', 'funbbb',
  'cyrilhanouna', 'rezaabdolmaleki2020', 'the_undisputed', 'tuxobmd', 'rbabakchess13642030', 'dragon14', 'ironcrow', 'missz', 'mk58', 'poci', 'etudeopus', 'archito', 'thebarghest', 'ironman3000', 'lenin1970', 'stevn',
  'alekhine316', 'eloy30', 'morphy_rage', 'joselpb', 'jedivampa', 'fallistoh', 'sashafdfdfdsdfavds', 'jp_neto', 'obsceeniity', 'trump61', 'josefmd', 'minigamesonly', 'i_king-kong_i', 'fallen2ryze1', 'nes0901', 'acaki',
  'mehrdad95', 'apo2016', 'rezaabdolmaleki1234', 'shinekas', 'mihkael', 'prawer', 'wildtornado', 'esmir21', 'f117nighthawk', 'wigbang', 'xxxtentacion332', 'rip_my_elo', 'selenaaaaa', 'leboncoin', 'culm_check', 'murfy',
  'cornkillamd', 'chesterking05', 'jack_bauer', 'jb0x', 'rafaelleitao', 'jrh201', 'sturkian7', 'agrig19_chess', 'destruidor10', 'fischerrocks', 'bubmix', 'mehrab-56', 'asahina_aoi', 'cansaglam01', 'mohammadhosein1380',
  'picodellamirandola64', 'ssbz', 'anab_69', 'korchnoi_2018', 'shahrom223', 'pumbaa80', 'kevlancelot67', 'lazarz', 'rhdhhehud', 'tigertigran', 'royal16', 'igornataf', 'diegocayon', 'mokara', 'vesna999', 'lonewolf2017',
  'itswhatever', 'nataf251270', 'im54n', 'chessbasten', 'igor2', 'blackfreed', 'metinbaba24', 'thewayiam', 'mamaasdfasdf', 'riderfm', 'rogercamp', 'roubick', 'habip_2001', 'psychoticdreamz', 'prio', 'the-spins',
  'starkerspieler', 'lilianebettencourt', 'simontrix', 'xxxtentacion228', 'ngaingai', 'vinay093876', 'muziking', 'khadivi2016', 'beepbeep2017', 'freedom1987', 'agrig1991', 'wael_elawamy', 'alecast', 'stoutlaw',
  'funtikforever', 'persevere11', 'baris2145', 'luis_alfredop', 'abdulaziz123', 'tays', 'shvamix', 'memasmimas', 'losalarambaug', 'aakcaozoglu', 'highmorphy', 'landedman', 'serious_black07', 'shinichi_izumi',
  'm7mmd3bbas3', 'ibr4x4', 'jinxed1t', 'genesis2017', 'bediiiesssss', 'nkurek02', 'fc_dinamo_moskva', 'rekikismail', 'anneke_peter', 'sinam', 'k2052', 'mytariniel', 'almahdi', 'as1988', 'therpm69', 'alaaalnahal',
  'therpm420', 'therpm267', 'kekoza', 'vdstef7777', 'dvornikov_sergei', 'rudkhan_castle', 'lyubovsmirnova', 'irashahmats', 'cellosuite', 'jakomo0505', 'stanislavkov', 'mr1367', 'rostandastan', 'fujydeniz', 'maciejovsky',
  'segzytshepo', 'jiggyjigga', 'giannimorte', 'ehabyasin', 'yalnizsincap', 'snowdenix', 'chessbuggy', 'sadeer', 'chal1iwel1', 'cha11iwe11', 'oreo_green', 'zengan46', 'kenalan_donk1', 'moiseyoys', 'kingofhyperbullet',
  'di_chess_g', 'iron_savage', 'unbreakable_castle', 'horrible_castle', 'dark_skul', 'horrible_skull', 'extreme_acropolis', 'steel_castle', 'lordark', 'brings', 'jcleclaire', 'razziyi', 'xuuy', 'k1nq0fl0rd38',
  'suetam99', 'diaszhumabaev', 'owlbufi', 'norbert_kurek', 'amirmaster2', 'zzznerdzzz', 'steel_stronghold', 'marju18', 'meilleurquecarlsen', 'dfgp', 'joes-king', 'vitwaschess', 'xxxtentacion221', 'anirudh13',
  'roman_diogen', 'vissenbesser', 'koval1001', 'calebaparicio', 'adamhimself', 'arkaitzvdb', 'avgreenarrow2', 'mandriva', 'pauldetarse', 'tyeanot', 'smurfsmurf', 'veryswift', 'cubic2017', 'm__i__l__e__s', 'pancakespk',
  'solipsismal', 'hernangparra', 'nikola_babo_za_sah', 'enginyapici', 'setconvar', 'maminmo', 'darthvader666', 'brandonhewer', 'ponychess', 'renren29', 'wasesa45', 'kingscrusher2003', 'onlyvictory', 'gaei',
  'pavelzubakin', 'ewgen79m', 'petros161', 'vlad95', 'artle2020', 'karadjoz', 'bobobobev123456', 'brshrdl', 'abasgholizadeh', 'garry2512', 'tigerclay', 'maratik05', 'jrk22', 'bibragimovich', 'phoder2', 'sergiofil070',
  'mayweather_tmt', 'bilalmasri', 'akula1979', 'oldman', 'obeynab', 'bishop_01', 'shahrom2', 'risemyminions', 'rd123', 'poilk22', 'yassinox', 'various', 'emprescue', 'bambinosaur', 'thinktactics', 'whiteknightf3',
  'deagol', 'iva-v', 'joe-boys-king', 'gabsterwii', 'franciscopizarro', 'parthia', 'dries02', 'snees', 'bboyaggi', 'martinec_tamas', 'nokikala200', 'ewen_steiner', 'sergirovad', 'emreselcuk38', 'vavanou', 'dundee52',
  'lamoto', 'maslukman', 'lifecrew', 'check_angel_tr', 'fether37', 'turk37', 'pillock', 'eamarba', 'marmotine', 'krotart77', 'ngncfc', 'akisemar', 'pythondeveloper', 'zionmakubex', 'blue_whale', 'fardos', 'darklord0408',
  'cruxchess', 'viento617', 'qwerty1337222', 'assedio99', 'chessnoob999', 'annutara', 'mendezkevone06', 'pawnewbie', 'luccas_piola', 'fantastik52', 'nsynkk', 'dnpnik', 'dagonchess', 'sassanid', 'superstarone',
  'sean_connery1', 'yetanothergm', 'renatobsb', 'kqueen1987', 'romario_oo', 'grandjazz', 'objorkman', 'alwin14', 'tejavishnuvardhan', 'elmerc3ss', 'kongloki', 'efendi0620', 'abfert', 'roman562128duksa', 'nachitoecem',
  'wahidafg', 'rateodoro', 'ijk251270', 'e2-e4_e7-e5', 'antifragile', 'zaydmaes2006', 'zaadneemt420', 'maximusresource', 'fafa1', 'chasem87', 'magnuscarlsentr', 'amir_sorena', 'aminesteghlal2', 'theyellowking',
  'buaytz', 'xlopu6ka', 'ej2000', 'yubill76', 'elislo', 'hunterkiller_pt', 'artiblek', 'artempronkin_121', 'traversyl', 'freniter35', 'askar_jubatov', 'bazande-1', 'panterrrra', 'mygodimdece', 'kontrabas',
  'niko_perusko', 'ariyan_sharifi', 'justresign7', 'fukmjuzzz', 'karlsen1989', 'ertugrul231963', 'ddd207', 'ushtaric7', 'linkerbaan', 'beatiful_agony']
#engines.reverse()
engines = iter(engines)

env.irwin.train()

while True:
  # Get player data
  #userId = env.api.getPlayerId()
  userId = next(engines, None)
  userData = env.api.getPlayerData(userId)

  # Filter games and assessments for relevant info
  try:
    pas = list([PlayerAssessmentBSONHandler.reads(pa) for pa in userData['assessment']['playerAssessments']])
    playerAssessments = PlayerAssessments(pas)
    games = recentGames(playerAssessments, userData['games'])
  except KeyError:
    continue # if either of these don't gather any useful data, skip them

  # Write stuff to mongo
  env.playerAssessmentDB.lazyWriteMany(playerAssessments)
  env.gameDB.lazyWriteGames(games)

  # Pull everything from mongo that we have on the player
  playerAssessments = env.playerAssessmentDB.byUserId(userId)
  games = env.gameDB.byIds(playerAssessments.gameIds())
  gameAnalyses = env.gameAnalysisDB.byUserId(userId)

  logging.debug(bcolors.WARNING + "Already Analysed: " + str(len(gameAnalyses.gameAnalyses)) + bcolors.ENDC)

  for g in games.games:
    if playerAssessments.hasGameId(g.id):
      gameAnalyses.append(GameAnalysis(g, playerAssessments.byGameId(g.id), [], []))

  gameAnalyses.analyse(env.engine, env.infoHandler)

  playerAnalysis = PlayerAnalysis(
    id = userId,
    titled = 'titled' in userData['assessment']['user'].keys(),
    engine = isEngine(userData),
    gamesPlayed = userData['assessment']['user']['games'],
    closedReports = sum(1 if r.get('processedBy', None) is not None else 0 for r in userData['history'] if r['type'] == 'report' and r['data']['reason'] == 'cheat'),
    gameAnalyses = gameAnalyses)

  env.playerAnalysisDB.write(playerAnalysis)
  env.gameAnalysisDB.lazyWriteGames(gameAnalyses)