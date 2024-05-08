import multiprocessing

import chess
import re
import time
import random

positions = []


def check_if_in_fen_list_pawns(fen_list, search_position):
    for fen in fen_list:
        pawns_position = fen.split(' ')[0]
        search_position_pawns = search_position.split(' ')[0]
        if pawns_position == search_position_pawns:
            return True
    return False


def check_for_draw(board):
    if board.is_stalemate():
        return True
    return False


def calculate_depth(board, times):
    wtime = times[0]
    btime = times[1]

    if board.turn == chess.WHITE and int(wtime) < 5000:
        return 1
    elif board.turn == chess.BLACK and int(btime) < 5000:
        return 1
    elif board.turn == chess.WHITE and int(wtime) < 30000:
        return 2
    elif board.turn == chess.BLACK and int(btime) < 30000:
        return 2
    elif board.turn == chess.WHITE and int(wtime) < 60000:
        return 3
    elif board.turn == chess.BLACK and int(btime) < 60000:
        return 3

    else:
        return 3


def heuristic_sort_moves(board, legal_moves):
    sorted_moves = []
    if board.turn == chess.WHITE:
        for move in legal_moves:
            board.push(move)
            move_score = scan(board, 1, int(-999999999))
            board.pop()
            sorted_moves.append((move, move_score))
    elif board.turn == chess.BLACK:
        for move in legal_moves:
            board.push(move)
            move_score = scan(board, 1, int(999999999))
            board.pop()
            sorted_moves.append((move, move_score))

    sorted_moves.sort(key=lambda x: x[1], reverse=board.turn == chess.WHITE)

    return [move for move, _ in sorted_moves]

def evaluation(board):
    # Przykładowa ocena pozycji.
    piece_values = {
        chess.PAWN: [100, 120, 140, 160, 180, 200, 220, 240, 260],  # Wartości pionów w zależności od ich pozycji
        chess.KNIGHT: 300,
        chess.BISHOP: 300,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 0
    }

    if board.is_checkmate():
        if board.turn == chess.WHITE:
            score = -999999  # Czarny wygrywa, więc przypisz dużą negatywną wartość
            return score
        else:
            score = +999999
            return score
    else:
        score = 0

    # Sprawdź, ile jest figur na planszy
    num_pieces = sum(1 for square in chess.SQUARES if board.piece_at(square) is not None)

    pawn_punishment = (10 - board.fullmove_number) * 200

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None:
            continue

        if piece.color == chess.WHITE:
            if piece.piece_type == chess.PAWN:
                # Dla pionów oblicz wartość na podstawie ich pozycji
                if chess.square_file(square) in {3, 4} or board.fullmove_number > 10:
                    row = chess.square_rank(square)
                    score += piece_values[piece.piece_type][row]
            elif piece.piece_type != chess.QUEEN and board.fullmove_number < 13 and square == 59:
                score -= 400
            else:
                score += piece_values[piece.piece_type]

            # Jeśli jest mniej niż 4 figury, nagradzaj zbliżanie króla do króla przeciwnika
            if num_pieces < 4:
                king_distance = chess.square_distance(square, board.king(chess.BLACK))
                score += 3 * king_distance

        else:
            if piece.piece_type == chess.PAWN:
                # Dla pionów oblicz wartość na podstawie ich pozycji
                if chess.square_file(square) in {3, 4} or board.fullmove_number > 10:
                    row = 9 - chess.square_rank(square)
                    score -= piece_values[piece.piece_type][row]
            elif piece.piece_type != chess.QUEEN and board.fullmove_number < 13 and square == 3:
                score += 400
            else:
                score -= piece_values[piece.piece_type]

            # Jeśli jest mniej niż 4 figury, nagradzaj zbliżanie króla do króla przeciwnika
            if num_pieces < 4:
                king_distance = chess.square_distance(square, board.king(chess.WHITE))
                score -= 3 * king_distance

    move_count = len(list(board.legal_moves))

    if board.turn == chess.WHITE:
        score += move_count * 2
        opp_king_sq = board.king(chess.BLACK)
        if opp_king_sq in [chess.A1, chess.A2, chess.A3, chess.A4, chess.A5, chess.A6, chess.A7, chess.A8] and \
                opp_king_sq in [chess.H1, chess.H2, chess.H3, chess.H4, chess.H5, chess.H6, chess.H7, chess.H8] and \
                opp_king_sq in [chess.B1, chess.C1, chess.D1, chess.E1, chess.F1, chess.B8, chess.C8, chess.D8,
                                chess.E8, chess.F8]:
            score += 50  # Dodaj punkty za króla przeciwnika blisko wszystkich krawędzi
    else:
        score -= move_count
        opp_king_sq = board.king(chess.WHITE)
        if opp_king_sq in [chess.A1, chess.A2, chess.A3, chess.A4, chess.A5, chess.A6, chess.A7, chess.A8] and \
                opp_king_sq in [chess.H1, chess.H2, chess.H3, chess.H4, chess.H5, chess.H6, chess.H7, chess.H8] and \
                opp_king_sq in [chess.B1, chess.C1, chess.D1, chess.E1, chess.F1, chess.B8, chess.C8, chess.D8,
                                chess.E8, chess.F8]:
            score -= 50  # Dodaj punkty za króla przeciwnika blisko wszystkich krawędzi

    castle_bonus = ((12 - board.fullmove_number) * 10) + 200

    if castle_bonus > 0:

        if board.king(chess.WHITE) in [chess.C1, chess.G1]:
            score += castle_bonus

        if board.king(chess.BLACK) in [chess.C8, chess.G8]:
            score -= castle_bonus

    if board.is_stalemate():
        score = 0

    # Nagradzaj, gdy król przeciwnika jest blisko wszystkich czterech krawędzi

    if check_if_in_fen_list_pawns(positions, board.fen()) in positions:
        score = 0

    if check_for_draw(board):
        score = 0

    return score


def scan(board, depth, current_max_evaluation):
    if depth == 0:
        return evaluation(board)

    if board.is_checkmate() or check_for_draw(board):
        return evaluation(board)

    legal_moves = list(board.legal_moves)

    if depth > 2:
        legal_moves = heuristic_sort_moves(board, legal_moves)

    if board.turn == chess.WHITE:
        max_evaluation = int(-999999999)
        for move in legal_moves:
            board.push(move)
            current_evaluation = scan(board, depth - 1, max_evaluation)
            board.pop()
            if current_evaluation > current_max_evaluation:
                return current_evaluation
            if current_evaluation > max_evaluation:
                max_evaluation = current_evaluation
        return max_evaluation
    elif board.turn == chess.BLACK:
        max_evaluation = int(999999999)
        for move in legal_moves:
            board.push(move)
            current_evaluation = scan(board, depth - 1, max_evaluation)
            board.pop()
            if current_evaluation < current_max_evaluation:
                return current_evaluation
            if current_evaluation < max_evaluation:
                max_evaluation = current_evaluation
        return max_evaluation


def best_move(board, depth):
    legal_moves = list(board.legal_moves)
    best = None
    best_result = []

    legal_moves = heuristic_sort_moves(board, legal_moves)

    if board.turn == chess.WHITE:
        max_evaluation = int(-999999999)
        pool_args = [(board.copy(), depth, max_evaluation, move) for move in legal_moves]
        with multiprocessing.Pool() as pool:
            results = pool.map(scan_wrapper, pool_args)

        best_result = max(results, key=lambda x: x[0])
        best = best_result[1]

    if board.turn == chess.BLACK:
        max_evaluation = int(999999999)
        pool_args = [(board.copy(), depth, max_evaluation, move) for move in legal_moves]
        with multiprocessing.Pool() as pool:
            results = pool.map(scan_wrapper, pool_args)

        best_result = min(results, key=lambda x: x[0])
        best = best_result[1]

    board.push(best)
    if board.is_stalemate():
        best = best_result[2]
    board.pop()

    return best


def scan_wrapper(args):
    board, depth, alpha_beta_value, move = args
    board.push(move)
    current_evaluation = scan(board, depth, alpha_beta_value)
    board.pop()
    return current_evaluation, move


def main():
    board = chess.Board()
    while True:
        command = input()

        if command.startswith("uci"):
            print("uciok")
        elif command.startswith("isready"):
            print("readyok")
        elif command.startswith("position"):
            parts = command.split()
            if len(parts) >= 2 and parts[1] == "startpos":
                board.reset()
                if len(parts) > 2 and parts[2] == "moves":
                    for move in parts[3:]:
                        board.push_uci(move)
            elif len(parts) >= 2 and parts[1] == "fen":
                fen = " ".join(parts[2:8])
                board.set_fen(fen)
                if len(parts) > 8 and parts[8] == "moves":
                    for move in parts[9:]:
                        board.push_uci(move)
        elif command.startswith("go"):
            start_time = time.time()
            if "wtime" in command:
                times = re.findall(r'\d+', command)
                depth = calculate_depth(board, times)
            else:
                depth = 3
            if board.fullmove_number < 2:
                depth = 3

            num_pieces = sum(1 for square in chess.SQUARES if board.piece_at(square) is not None)
            if num_pieces < 6 and depth % 2 == 1:
                depth += 1
            if board.fullmove_number == 1 and board.turn == chess.WHITE:
                moves = list(list(board.legal_moves)[i] for i in [1, 15])
                move = random.choice(moves)
            else:
                move = best_move(board, depth)
            positions.append(board.fen())
            end_time = time.time()
            execution_time_ms = (end_time - start_time) * 1000
            print(f"bestmove {move.uci()}")
            # print(f"Function execution time: {execution_time_ms:.2f} milliseconds")

        elif command.startswith("ping"):
            parts = command.split()
            if len(parts) == 2:
                print("pong", parts[1])
        elif command == "quit":
            break


main()
